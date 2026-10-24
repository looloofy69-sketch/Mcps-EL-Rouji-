import unittest


class ServerImportTests(unittest.TestCase):
    def test_mcp_server_registers(self) -> None:
        from el_rouji_mcp import server

        self.assertIsNotNone(server.mcp)
        self.assertTrue(callable(server.main))


if __name__ == "__main__":
    unittest.main()
