"""PC-012: deleting a workspace (a purged project, a deleted account) leaves nothing running or on disk."""

import tempfile
import threading
import urllib.request
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.studio.server import StudioWorkspaceStore, create_studio_server


class DeletingAWorkspaceStopsItsPreviewFirst(TestCase):
    def test_the_preview_stops_before_the_folder_goes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StudioWorkspaceStore(Path(tmp))
            store.ensure_workspace("ws-gone")
            order: list[str] = []

            def stop(ws_id: str) -> dict:
                # A running dev server would write .next/ and logs/ back into the folder.
                order.append("stop" if store.workspace_dir(ws_id).exists() else "stop-too-late")
                return {"status": "stopped"}

            server = create_studio_server(lambda _p: {}, host="127.0.0.1", port=0,
                                          workspace_store=store, workspace_preview_stop_fn=stop)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                request = urllib.request.Request(
                    f"http://127.0.0.1:{server.server_port}/api/workspaces/ws-gone", method="DELETE")
                with urllib.request.urlopen(request, timeout=10) as response:
                    self.assertEqual(response.status, 200)
            finally:
                server.shutdown()
            self.assertEqual(order, ["stop"])
            self.assertFalse(store.workspace_dir("ws-gone").exists())
