import pytest
from omega_kg.parsers import parse_html_content

def test_ai_studio_parsing():
    html = """
    <html>
        <body>
            <div class="message-user">User: Hello</div>
            <div class="message-model">Model: Hi there</div>
            <div class="irrelevant">Sidebar content</div>
        </body>
    </html>
    """
    messages = parse_html_content(html, "https://aistudio.google.com/test")
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "User: Hello"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Model: Hi there"

def test_nano_gpt_parsing():
    html = """
    <html>
        <body>
            <div class="user-message-container">
                <div class="whitespace-pre-wrap">User Question</div>
            </div>
            <div class="bot-message-container">
                <div class="whitespace-pre-wrap">Bot Answer</div>
            </div>
        </body>
    </html>
    """
    messages = parse_html_content(html, "https://nano-gpt.com/chat")
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "User Question"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Bot Answer"

def test_nano_gpt_parsing_robustness():
    # Test that it doesn't rely on even/odd index
    html = """
    <html>
        <body>
            <div class="bot-message-container">
                <div class="whitespace-pre-wrap">System Welcome</div>
            </div>
            <div class="user-message-container">
                <div class="whitespace-pre-wrap">User Reply</div>
            </div>
        </body>
    </html>
    """
    messages = parse_html_content(html, "https://nano-gpt.com/chat")
    assert len(messages) == 2
    assert messages[0]["role"] == "assistant" # Should be assistant/system
    assert messages[0]["content"] == "System Welcome"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "User Reply"

def test_generic_fallback():
    html = """
    <html>
        <body>
            <p>Paragraph 1</p>
            <p>Paragraph 2</p>
        </body>
    </html>
    """
    messages = parse_html_content(html, "https://example.com")
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "assistant"
    assert "Paragraph 1" in messages[1]["content"]
    assert "Paragraph 2" in messages[1]["content"]
