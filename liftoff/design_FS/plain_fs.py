class FileSystem:
    def __init__(self):
        self.root = {'type': 'dir', 'children': {}}

    def _resolve_path(self, path):
        if path == '/':
            return self.root
        parts = path.split('/')[1:]
        current = self.root
        for part in parts:
            if part not in current['children']:
                return None
            current = current['children'][part]
        return current

    def _resolve_parent_and_name(self, path):
        if path == '/':
            return None, None  # root has no parent
        parts = path.split('/')
        name = parts[-1]
        parent_path = '/'.join(parts[:-1]) if len(parts) > 1 else '/'
        parent = self._resolve_path(parent_path)
        return parent, name

    def mkdir(self, path: str) -> None:
        parent, name = self._resolve_parent_and_name(path)
        if parent is None:
            if path == '/':
                return  # root already exists
            else:
                raise ValueError("Parent directory does not exist")
        if parent['type'] != 'dir':
            raise ValueError("Parent is not a directory")
        if name in parent['children']:
            return  # directory already exists
        parent['children'][name] = {'type': 'dir', 'children': {}}

    def addFile(self, path: str, content: str) -> None:
        parent, name = self._resolve_parent_and_name(path)
        if parent is None:
            raise ValueError("Parent directory does not exist")
        if parent['type'] != 'dir':
            raise ValueError("Parent is not a directory")
        if name in parent['children'] and parent['children'][name]['type'] == 'dir':
            raise ValueError("Directory with same name exists")
        parent['children'][name] = {'type': 'file', 'content': content}

    def readFile(self, path: str) -> str:
        node = self._resolve_path(path)
        if not node or node['type'] != 'file':
            raise ValueError("File not found")
        return node['content']

    def ls(self, path: str) -> list[str]:
        node = self._resolve_path(path)
        if not node:
            raise ValueError("Path not found")
        if node['type'] == 'file':
            return [path.split('/')[-1]]
        else:
            return sorted(node['children'].keys())