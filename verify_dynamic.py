
import os
import unittest
from unittest.mock import MagicMock, patch
from main import handle_method, search_knowledge_base, DATA_STORE_ID

class TestMCPDynamicKB(unittest.TestCase):
    
    @patch('main.discoveryengine')
    def test_default_kb_id(self, MockDiscoveryEngine):
        """Test fallback to default DATA_STORE_ID when no ID provided."""
        MockClient = MockDiscoveryEngine.SearchServiceClient
        mock_instance = MockClient.return_value
        mock_instance.search.return_value.results = []
        mock_instance.search.return_value.summary.summary_text = ""
        
        # 1. Direct function call
        search_knowledge_base("test query")
        
        # Verify default ID was used
        args, kwargs = mock_instance.serving_config_path.call_args
        self.assertEqual(kwargs['data_store'], DATA_STORE_ID)
        
    @patch('main.discoveryengine')
    def test_dynamic_kb_id(self, MockDiscoveryEngine):
        """Test usage of provided data_store_id."""
        MockClient = MockDiscoveryEngine.SearchServiceClient
        mock_instance = MockClient.return_value
        mock_instance.search.return_value.results = []
        mock_instance.search.return_value.summary.summary_text = ""
        
        custom_id = "custom-store-123"
        
        # 1. Direct function call
        search_knowledge_base("test query", data_store_id=custom_id)
        
        # Verify custom ID was used
        args, kwargs = mock_instance.serving_config_path.call_args
        self.assertEqual(kwargs['data_store'], custom_id)

    @patch('main.discoveryengine')
    def test_handle_method_propagation(self, MockDiscoveryEngine):
        """Test data_store_id propagation via handle_method."""
        MockClient = MockDiscoveryEngine.SearchServiceClient
        mock_instance = MockClient.return_value
        mock_instance.search.return_value.results = []
        mock_instance.search.return_value.summary.summary_text = ""
        
        custom_id = "via-api-456"
        
        # Call via tool interface
        handle_method("tools/call", {
            "name": "search_vertex_docs",
            "arguments": {
                "query": "something",
                "data_store_id": custom_id
            }
        })
        
        # Verify custom ID reached the client
        args, kwargs = mock_instance.serving_config_path.call_args
        self.assertEqual(kwargs['data_store'], custom_id)

    @patch('main.discoveryengine')
    def test_env_var_override(self, MockDiscoveryEngine):
        """Test environment variable overrides default but is overridden by argument."""
        MockClient = MockDiscoveryEngine.SearchServiceClient
        mock_instance = MockClient.return_value
        mock_instance.search.return_value.results = []
        mock_instance.search.return_value.summary.summary_text = ""
        
        env_id = "env-store-789"
        arg_id = "arg-store-000"
        
        with patch.dict(os.environ, {"VERTEX_DATA_STORE_ID": env_id}):
            # Case A: No arg -> Use Env
            search_knowledge_base("test")
            args, kwargs = mock_instance.serving_config_path.call_args
            self.assertEqual(kwargs['data_store'], env_id)
            
            # Case B: With arg -> Use Arg (ignore Env)
            search_knowledge_base("test", data_store_id=arg_id)
            args, kwargs = mock_instance.serving_config_path.call_args
            self.assertEqual(kwargs['data_store'], arg_id)

if __name__ == '__main__':
    unittest.main()
