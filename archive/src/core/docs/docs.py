"""Documentation system for the arbitrage bot."""

class DocsSystem:
    """System for managing API documentation."""

    def __init__(self):
        """Initialize the documentation system."""
        self.endpoints = {
            '/api/analytics/performance': {
                'method': 'GET',
                'description': 'Get performance metrics',
                'parameters': [],
                'responses': {
                    '200': {
                        'description': 'Success',
                        'schema': {
                            'type': 'object',
                            'properties': {
                                'total_trades': {'type': 'integer'},
                                'successful_trades': {'type': 'integer'},
                                'failed_trades': {'type': 'integer'},
                                'total_profit_usd': {'type': 'string'},
                                'total_gas_cost_eth': {'type': 'string'},
                                'success_rate': {'type': 'string'}
                            }
                        }
                    }
                }
            }
        }

        self.schemas = {
            'PerformanceMetrics': {
                'type': 'object',
                'properties': {
                    'total_trades': {'type': 'integer'},
                    'successful_trades': {'type': 'integer'},
                    'failed_trades': {'type': 'integer'},
                    'total_profit_usd': {'type': 'string'},
                    'total_gas_cost_eth': {'type': 'string'},
                    'success_rate': {'type': 'string'}
                }
            }
        }

        self.guides = [
            {
                'title': 'Getting Started',
                'path': '/docs/guides/getting-started',
                'sections': [
                    {
                        'title': 'Introduction',
                        'content': 'Welcome to the arbitrage bot API documentation.'
                    },
                    {
                        'title': 'Authentication',
                        'content': 'Learn how to authenticate with the API.'
                    }
                ]
            }
        ]

        self.examples = [
            {
                'title': 'Authentication',
                'language': 'python',
                'code': '''
import requests

api_key = 'your_api_key'
headers = {'Authorization': f'Bearer {api_key}'}

response = requests.get('http://localhost:5000/api/analytics/performance', headers=headers)
data = response.json()
print(data)
''',
                'description': 'Example of authenticating with the API and fetching performance metrics.'
            }
        ]

    def get_api_endpoints(self):
        """Get API endpoint documentation."""
        return self.endpoints

    def get_api_schemas(self):
        """Get API schema documentation."""
        return self.schemas

    def get_api_guides(self):
        """Get API guides and tutorials."""
        return self.guides

    def get_api_examples(self):
        """Get API usage examples."""
        return self.examples
