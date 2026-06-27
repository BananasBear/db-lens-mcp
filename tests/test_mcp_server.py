from db_lens_mcp.mcp.tools import register_tools


class FakeMcpServer:
    def __init__(self) -> None:
        self.tools = []

    def tool(self):
        def decorator(func):
            self.tools.append(func.__name__)
            return func

        return decorator


def test_register_tools_adds_first_phase_tool_surface() -> None:
    server = FakeMcpServer()

    register_tools(server)

    assert server.tools == [
        "list_databases",
        "list_tables",
        "describe_table",
        "list_indexes",
        "get_table_stats",
        "explain_select",
        "inspect_query",
    ]
