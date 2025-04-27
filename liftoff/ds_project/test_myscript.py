import pdb
import unittest
from data_store import CountingStore


class TestCountingStore(unittest.TestCase):
    def setUp(self):
        self.store = CountingStore()

    def run_script(self, commands):
        outputs = []
        for line in commands:
            out = self.store.process_command(line)
            if out:
                outputs.append(out)
        return outputs

    def test_write_read_countval(self):
        cmds = [
            "WRITE a 1",
            "WRITE b 1",
            "WRITE c 2",
            "READ a",
            "READ b",
            "READ x",
            "COUNTVAL 1",
            "COUNTVAL 2",
            "COUNTVAL 3"
        ]
        expected = ["1", "1", "No value", "2", "1", "0"]
        result = self.run_script(cmds)
        self.assertEqual(result, expected)

    def test_checkpoint_revert(self):
        cmds = [
            "WRITE a 5",
            "CHECKPOINT",
            "WRITE a 10",
            "READ a",
            "REVERT",
            "READ a",
            "REVERT"
        ]
        expected = ["10", "5", "Nothing to revert"]
        result = self.run_script(cmds)
        self.assertEqual(result, expected)

    def test_multiple_reverts(self):
        cmds = [
            "WRITE a 1",
            "CHECKPOINT",
            "WRITE a 2",
            "CHECKPOINT",
            "WRITE a 3",
            "READ a",
            "REVERT",
            "READ a",
            "REVERT",
            "READ a"
        ]
        expected = ["3", "2", "1"]
        result = self.run_script(cmds)
        self.assertEqual(result, expected)

    def test_countval_after_reverts(self):
        cmds = [
            "WRITE x 10",
            "WRITE y 10",
            "COUNTVAL 10",
            "CHECKPOINT",
            "WRITE x 20",
            "COUNTVAL 10",
            "REVERT",
            "COUNTVAL 10"
        ]
        expected = ["2", "1", "2"]
        result = self.run_script(cmds)
        self.assertEqual(result, expected)
    
    def test_save_load(self):
        import os
        filename = "temp_test_state.json"
        if os.path.exists(filename):
            os.remove(filename)

        self.run_script([
            "WRITE a 100",
            "CHECKPOINT",
            "WRITE a 200",
            f"SAVE {filename}",
            "WRITE a 300"
        ])
        self.assertEqual(self.store.read("a"), "300")

        self.run_script([f"LOAD {filename}"])
        self.assertEqual(self.store.read("a"), "200")

        self.run_script(["REVERT"])
        self.assertEqual(self.store.read("a"), "100")

        result = self.store.process_command("REVERT")
        self.assertEqual(result, "Nothing to revert")

        if os.path.exists(filename):
            os.remove(filename)


    def test_script_file(self):
        import os

        current_dir = os.path.dirname(__file__)  # directory where script lives
        input_file_path = os.path.join(current_dir, "test_script.txt")
        output_file_path = os.path.join(current_dir, "expected_output.txt")

        with open(input_file_path, "r") as f:
            commands = f.readlines()

        with open(output_file_path, "r") as f:
            expected_output = [line.strip() for line in f.readlines()]

        actual_output = []
        pdb.set_trace()
        for command in commands:
            result = self.store.process_command(command)
            if result:
                actual_output.append(result)

        self.assertEqual(actual_output, expected_output)

if __name__ == "__main__":
    unittest.main()