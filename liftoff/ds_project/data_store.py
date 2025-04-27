import json
import os
import logging
import sys
from collections import defaultdict

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class CountingStore:
    def __init__(self):
        self.store = {}
        self.value_count = defaultdict(int)
        self.checkpoints = []
        logger.debug("Initialized CountingStore")

    def write(self, name: str, value):
        old_value = self.store.get(name)
        if old_value is not None:
            self.value_count[old_value] -= 1
        self.store[name] = value
        self.value_count[value] += 1

        if self.checkpoints:
            self.checkpoints[-1].append(('WRITE', name, old_value))

        logger.debug(f"WRITE: {name} = {value} (old: {old_value})")

    def read(self, name: str) -> str:
        value = self.store.get(name)
        logger.debug(f"READ: {name} => {value if value is not None else 'No value'}")
        return str(value) if value is not None else "No value"

    def countval(self, value) -> int:
        count = self.value_count.get(value, 0)
        logger.debug(f"COUNTVAL: {value} => {count}")
        return count

    def checkpoint(self):
        self.checkpoints.append([])
        logger.debug(f"CHECKPOINT created. Total: {len(self.checkpoints)}")

    def revert(self) -> str:
        if not self.checkpoints:
            logger.debug("REVERT: Nothing to revert")
            return "Nothing to revert"
        changes = self.checkpoints.pop()
        for action in reversed(changes):
            _, name, old_value = action
            new_value = self.store.get(name)
            if new_value is not None:
                self.value_count[new_value] -= 1
            if old_value is None:
                if name in self.store:
                    del self.store[name]
            else:
                self.store[name] = old_value
                self.value_count[old_value] += 1
        logger.debug(f"REVERT: Applied {len(changes)} changes. Checkpoints left: {len(self.checkpoints)}")
        return ""

    def save(self, filename: str):
        data = {
            "store": self.store,
            "value_count": dict(self.value_count),
            "checkpoints": self.checkpoints,
        }
        with open(filename, "w") as f:
            json.dump(data, f)
        logger.info(f"SAVE: State saved to '{filename}'")

    def load(self, filename: str):
        if not os.path.exists(filename):
            logger.error(f"LOAD: File not found - '{filename}'")
            return "Error: File not found"
        with open(filename, "r") as f:
            data = json.load(f)
            self.store = data["store"]
            self.value_count = defaultdict(int, data["value_count"])
            self.checkpoints = data["checkpoints"]
        logger.info(f"LOAD: State loaded from '{filename}'")

    def process_command(self, line: str) -> str:
        tokens = line.strip().split()
        if not tokens:
            return ""
        cmd = tokens[0].upper()
        args = tokens[1:]

        try:
            if cmd == "WRITE":
                self.write(args[0], int(args[1]))
                return ""
            elif cmd == "READ":
                return self.read(args[0])
            elif cmd == "COUNTVAL":
                return str(self.countval(int(args[0])))
            elif cmd == "CHECKPOINT":
                self.checkpoint()
                return ""
            elif cmd == "REVERT":
                msg = self.revert()
                return msg if msg else ""
            elif cmd == "SAVE":
                if len(args) != 1:
                    return "Error: SAVE requires a filename"
                self.save(args[0])
                return ""
            elif cmd == "LOAD":
                if len(args) != 1:
                    return "Error: LOAD requires a filename"
                msg = self.load(args[0])
                return msg if msg else ""
            else:
                return "Invalid command"
        except Exception as e:
            logger.exception("Error processing command")
            return f"Error: {str(e)}"

def main():
    store = CountingStore()
    for line in sys.stdin:
        store.process_command(line)
        # print(line)
        print(store.checkpoints)
        print(store.store)

def test_from_file():
    store = CountingStore()
    import os

    current_dir = os.path.dirname(__file__)  # directory where script lives
    input_file_path = os.path.join(current_dir, "test_script.txt")
    output_file_path = os.path.join(current_dir, "expected_output.txt")


    with open(input_file_path, "r") as cmd_file:
        commands = cmd_file.readlines()

    with open(output_file_path, "r") as output_file:
        expected = [line.strip() for line in output_file.readlines()]

    outputs = []
    for command in commands:
        result = store.process_command(command)
        if result:
            outputs.append(result)

    assert outputs == expected, f"\nExpected: {expected}\nGot: {outputs}"


def run_tests(input_commands, expected_output):
    import io, os

    filename = "state.db"
#     input_commands = f"""
# WRITE z 1
# CHECKPOINT
# WRITE z 2
# READ z
#     """

#     expected_output = """2
# """
    sys.stdin = io.StringIO(input_commands.strip())
    sys.stdout = io.StringIO()

    # store = CountingStore()
    # result = None
    # for line in sys.stdin:
    #     if line == "" or line == "\n":
    #         continue
    #     print("\ninputs are: " + line)
    #     result = store.process_command(line)
    #     print(store.checkpoints)
    #     print(store.store)
    # return result
    main()

    output = sys.stdout.getvalue()
    sys.stdin = sys.__stdin__
    sys.stdout = sys.__stdout__

    if os.path.exists(filename):
        os.remvoe(filename)

    # print("outs are: " + output.strip())
    # print("expected are: " + expected_output.strip())
    # print(output.strip() == expected_output.strip())
    return output.strip() == expected_output.strip()
    
"""
> WRITE z 1
> CHECKPOINT
> WRITE z 2
> READ z
2
> CHECKPOINT
> WRITE z 3
> READ z
3
> REVERT
> READ z
2
> REVERT
> READ z
1
> REVERT
Nothing to revert
> READ z
1
> COUNTVAL 1
1
> COUNTVAL 2
0

> WRITE x 10
> WRITE x 10
> COUNTVAL 10
1
> WRITE y 10
> COUNTVAL 10
2
"""


# input_commands_1 = f"""
# WRITE z 1
# CHECKPOINT
# WRITE z 2
# READ z
#     """

# expected_output_1= """2
# """

# # run_tests(input_commands_1, expected_output_1)

# input_commands_2 = input_commands_1 + "\n" + f"""
# CHECKPOINT
# WRITE z 3
# READ z
#     """

# expected_output_2= """3
# """
# run_tests(input_commands_2, expected_output_2)

# input_commands_3 = input_commands_1 + "\n" + f"""
# REVERT
# READ z
#     """

# expected_output_3= """2
# """
# run_tests(input_commands_3, expected_output_3)


# main()
test_from_file()


