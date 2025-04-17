# Brave Search MCP Server

This MCP server provides access to the Brave Search API, allowing you to perform web searches programmatically.

## Features

- Asynchronous API client with proper resource management
- Thread-safe implementation with locks
- Comprehensive error handling
- Proper cleanup of resources

## Setup

1. Ensure you have a Brave Search API key. You can obtain one from [Brave Search API](https://brave.com/search/api/).

2. Configure the API key in your `.env` file:
   ```
   # .env file
   BRAVE_API_KEY=your_api_key_here
   ```

3. The `.env` file is already included in `.gitignore` to ensure your API key is not committed to version control.

4. The MCP server is configured to use the environment variable in:
   - `.roo/mcp.json`
   - `.augment/mcp_config.json`

5. Never hardcode the API key in your code or commit it to version control.

## Usage

### Using the MCP Server

The MCP server exposes the following tools:

#### brave_web_search

Performs a web search using the Brave Search API.

**Parameters:**
- `query` (string, required): Search query (max 400 chars, 50 words)
- `count` (number, optional): Number of results (1-20, default 10)
- `offset` (number, optional): Pagination offset (max 9, default 0)

**Example:**
```json
{
  "query": "cryptocurrency arbitrage trading",
  "count": 5,
  "offset": 0
}
```

### Direct API Client Usage

You can also use the `BraveSearchClient` directly in your Python code:

```python
import os
import asyncio
from brave_search.brave_search_client import BraveSearchClient

async def main():
    # Get the API key from environment variable
    api_key = os.environ.get("BRAVE_API_KEY")
    if not api_key:
        print("Error: BRAVE_API_KEY environment variable is not set")
        return
    
    # Initialize the client with the API key from environment variable
    async with BraveSearchClient(api_key) as client:
        # Perform a web search
        results = await client.web_search("cryptocurrency arbitrage", count=5)
        
        # Process the results
        for result in results.get("web", {}).get("results", []):
            print(f"Title: {result.get('title')}")
            print(f"URL: {result.get('url')}")
            print(f"Description: {result.get('description')}")
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())
```

## Testing

You can test the Brave Search client using the provided test script:

```bash
python -m mcp_servers.brave_search.test_brave_search "your search query" 5
```

This will perform a search and display the results.

## API Response Structure

The Brave Search API returns results in the following structure:

```json
{
  "type": "search",
  "query": {
    "original": "your search query"
  },
  "total": 12345,
  "web": {
    "count": 5,
    "results": [
      {
        "title": "Result title",
        "url": "https://example.com",
        "description": "Result description",
        "age": "2023-01-01T00:00:00Z",
        "language": "en"
      },
      // More results...
    ]
  }
}
```

## Error Handling

The client and MCP server implement comprehensive error handling:

- API key validation
- Request validation
- API response validation
- Network error handling
- Resource cleanup

## Security Considerations

- The API key is sensitive information and should be kept secure
- Use environment variables or secure configuration for the API key
- Do not commit the API key to version control
- Consider implementing API key rotation

## Limitations

- The Brave Search API has rate limits that should be respected
- Maximum of 20 results per request
- Maximum offset of 9 (pagination)