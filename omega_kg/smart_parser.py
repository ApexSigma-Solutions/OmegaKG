# omega_kg/smart_parser.py

import logging
import httpx
import frontmatter
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class LinearAPIError(Exception):
    """Exception raised when Linear API operations fail."""
    pass


class TaskParsingError(Exception):
    """Exception raised when task parsing fails."""
    pass


async def parse_and_create_task(task_file_path: Path) -> Dict[str, Any]:
    """
    Parse an Obsidian task note and create a corresponding Linear issue.
    
    Implements file-based locking using frontmatter status flags to prevent race conditions.
    The operation is idempotent - no duplicate issues will be created.
    
    Args:
        task_file_path (Path): Path to the Obsidian task note file
        
    Returns:
        Dict[str, Any]: Result containing success status and Linear issue details
        
    Raises:
        TaskParsingError: If the task file cannot be parsed or is invalid
        LinearAPIError: If Linear API operations fail
    """
    logger.info(f"Processing task file: {task_file_path}")
    
    # Step 1: Check if file exists
    if not task_file_path.exists():
        raise TaskParsingError(f"Task file not found: {task_file_path}")
    
    # Step 2: Load and parse the frontmatter
    try:
        with open(task_file_path, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
    except Exception as e:
        raise TaskParsingError(f"Failed to read task file {task_file_path}: {e}")
    
    # Step 3: Check for existing linear_id (idempotency check)
    if post.metadata.get('linear_id'):
        logger.info(f"Task already has Linear ID: {post.metadata['linear_id']}")
        return {
            'success': True,
            'message': 'Task already has Linear issue',
            'linear_id': post.metadata['linear_id'],
            'skipped': True
        }
    
    # Step 4: Check for pending status (race condition prevention)
    if post.metadata.get('linear_status') == 'pending':
        logger.warning(f"Task is already being processed (pending status): {task_file_path}")
        return {
            'success': False,
            'message': 'Task is already being processed',
            'skipped': True
        }
    
    # Step 5: Set pending status before API call (file-based locking)
    try:
        post.metadata['linear_status'] = 'pending'
        with open(task_file_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter.dumps(post))
        logger.info(f"Set pending status for task: {task_file_path}")
    except Exception as e:
        raise TaskParsingError(f"Failed to set pending status: {e}")
    
    try:
        # Step 6: Extract task information from frontmatter and content
        task_data = _extract_task_data(post)
        
        # Step 7: Create Linear issue via API
        linear_issue = await _create_linear_issue(task_data)
        
        # Step 8: Update task file with Linear ID and remove pending status
        post.metadata['linear_id'] = linear_issue['identifier']
        post.metadata['linear_url'] = linear_issue['url']
        post.metadata['linear_status'] = linear_issue['state']['name']
        
        # Remove the pending status since we're done
        if 'linear_status' in post.metadata and post.metadata['linear_status'] == 'pending':
            del post.metadata['linear_status']
        
        with open(task_file_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter.dumps(post))
        
        logger.info(f"Successfully created Linear issue {linear_issue['identifier']} for task: {task_file_path}")
        
        return {
            'success': True,
            'message': 'Linear issue created successfully',
            'linear_id': linear_issue['identifier'],
            'linear_url': linear_issue['url'],
            'task_file': str(task_file_path)
        }
        
    except Exception as e:
        # Step 9: Cleanup on failure - remove pending status
        try:
            # Reload the file in case it was modified elsewhere
            with open(task_file_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
            
            # Remove pending status
            if post.metadata.get('linear_status') == 'pending':
                del post.metadata['linear_status']
                
            with open(task_file_path, 'w', encoding='utf-8') as f:
                f.write(frontmatter.dumps(post))
                
            logger.info(f"Cleaned up pending status after failure: {task_file_path}")
        except Exception as cleanup_error:
            logger.error(f"Failed to cleanup pending status: {cleanup_error}")
        
        # Re-raise the original exception
        if isinstance(e, (LinearAPIError, TaskParsingError)):
            raise
        else:
            raise TaskParsingError(f"Unexpected error processing task: {e}")


def _extract_task_data(post: frontmatter.Post) -> Dict[str, Any]:
    """
    Extract task data from frontmatter and content.
    
    Args:
        post (frontmatter.Post): Parsed frontmatter post
        
    Returns:
        Dict[str, Any]: Task data for Linear API
        
    Raises:
        TaskParsingError: If required task data is missing
    """
    metadata = post.metadata
    content = post.content
    
    # Extract title - try multiple sources
    title = (
        metadata.get('title') or 
        metadata.get('uid') or 
        'Untitled Task'
    )
    
    # Extract description from content
    description = content.strip() if content else "No description provided"
    
    # Extract priority (Linear uses 0=No priority, 1=Urgent, 2=High, 3=Medium, 4=Low)
    priority_map = {
        'urgent': 1,
        'high': 2, 
        'medium': 3,
        'low': 4
    }
    priority = priority_map.get(metadata.get('priority', '').lower(), 0)
    
    # Extract labels/tags
    labels = metadata.get('tags', [])
    if isinstance(labels, str):
        labels = [labels]
    
    task_data = {
        'title': title,
        'description': description,
        'priority': priority,
        'labels': labels,
        'metadata': metadata
    }
    
    logger.debug(f"Extracted task data: {task_data}")
    return task_data


async def _create_linear_issue(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a Linear issue via GraphQL API.
    
    Args:
        task_data (Dict[str, Any]): Task data extracted from Obsidian note
        
    Returns:
        Dict[str, Any]: Linear issue data
        
    Raises:
        LinearAPIError: If Linear API call fails
    """
    from omega_kg.settings import get_settings
    settings = get_settings()
    
    if not settings.linear_api_key:
        raise LinearAPIError("Linear API key not configured")
    
    if not settings.linear_team_id:
        raise LinearAPIError("Linear team ID not configured")
    
    # GraphQL mutation to create an issue
    mutation = """
    mutation IssueCreate($input: IssueCreateInput!) {
        issueCreate(input: $input) {
            success
            issue {
                id
                identifier
                title
                description
                url
                state {
                    id
                    name
                }
                priority
                createdAt
                updatedAt
            }
        }
    }
    """
    
    # Prepare the input
    variables = {
        "input": {
            "title": task_data['title'],
            "description": task_data['description'],
            "teamId": settings.linear_team_id,
            "priority": task_data['priority']
        }
    }
    
    # Add project ID if configured
    if settings.linear_project_id:
        variables["input"]["projectId"] = settings.linear_project_id
    
    headers = {
        "Authorization": f"Bearer {settings.linear_api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "query": mutation,
        "variables": variables
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.linear.app/graphql",
                json=payload,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise LinearAPIError(f"Linear API returned status {response.status_code}: {response.text}")
            
            result = response.json()
            
            if "errors" in result:
                error_messages = [error.get("message", "Unknown error") for error in result["errors"]]
                raise LinearAPIError(f"Linear API errors: {', '.join(error_messages)}")
            
            if not result.get("data", {}).get("issueCreate", {}).get("success"):
                raise LinearAPIError("Linear issue creation was not successful")
            
            issue = result["data"]["issueCreate"]["issue"]
            logger.info(f"Created Linear issue: {issue['identifier']} - {issue['title']}")
            
            return issue
            
    except httpx.RequestError as e:
        raise LinearAPIError(f"HTTP request failed: {e}")
    except Exception as e:
        raise LinearAPIError(f"Unexpected error calling Linear API: {e}")


def validate_linear_config() -> bool:
    """
    Validate that Linear integration is properly configured.
    
    Returns:
        bool: True if Linear is configured, False otherwise
    """
    from omega_kg.settings import get_settings
    settings = get_settings()
    
    required_settings = [
        settings.linear_api_key,
        settings.linear_team_id
    ]
    
    return all(setting is not None for setting in required_settings)


async def batch_process_tasks(vault_path: Path, pattern: str = "*.md") -> Dict[str, Any]:
    """
    Process multiple task files in batch.
    
    Args:
        vault_path (Path): Path to Obsidian vault
        pattern (str): File pattern to match (default: "*.md")
        
    Returns:
        Dict[str, Any]: Batch processing results
    """
    if not validate_linear_config():
        raise LinearAPIError("Linear integration not properly configured")
    
    results = {
        'processed': 0,
        'created': 0,
        'skipped': 0,
        'errors': 0,
        'details': []
    }
    
    # Find all matching files
    task_files = list(vault_path.rglob(pattern))
    
    for task_file in task_files:
        try:
            result = await parse_and_create_task(task_file)
            
            results['processed'] += 1
            if result.get('skipped'):
                results['skipped'] += 1
            else:
                results['created'] += 1
                
            results['details'].append({
                'file': str(task_file),
                'result': result
            })
            
        except Exception as e:
            results['errors'] += 1
            results['details'].append({
                'file': str(task_file),
                'error': str(e)
            })
            logger.error(f"Failed to process {task_file}: {e}")
    
    logger.info(f"Batch processing complete: {results['processed']} processed, "
                f"{results['created']} created, {results['skipped']} skipped, "
                f"{results['errors']} errors")
    
    return results