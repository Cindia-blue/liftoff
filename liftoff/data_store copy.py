import sys
import copy
import collections
import pickle

class CountingStore:
    def __init__(self):
        self.store = {}
        self.value_count = collections.defaultdict(int)
        self.checkpoints = []

    def write(self, name, value):
        old_value = self.store.get(name)
        if old_value is not None:
            self.value_count[old_value] -= 1
        self.store[name] = value
        self.value_count[value] += 1
    
        if self.checkpoints:
            self.checkpoints[-1].append(('WRITE', name, old_value))
        
    def read(self, name):
        if name in self.store:
            print(self.store[name])
        else:
            print("no value")
    
    def countval(self, value):
        print(self.value_count.get(value, 0))
    
    def checkpoint(self):
        self.checkpoints.append([])
    
    def revert(self):
        if not self.checkpoints:
            print("Nothing to revert")
            return
        
        changes = self.checkpoints.pop()
        for action in reversed(changes):
            _, name, old_value = action
            new_value = self.store.get(name)
            if new_value is not None:
                self.value_count[new_value] -= 1
            if old_value is None:
                del self.store[name]
            else:
                self.store[name] = old_value
                self.value_count[old_value] += 1
    
    def save(self, filename):
        with open(filename, 'wb') as f:
            pickle.dump((self.store, self.value_count, self.checkpoints), f)
        
    def load(self, filename):
        try:
            with open(filename, 'rb') as f:
                self.store, self.value_count, self.checkpoints = pickle.load(f)
        except FileNotFoundError:
            print("File not found")
        
    
    def process_command(self, command_line):
        tokens = command_line.strip().split()
        if not tokens:
            return
        cmd = tokens[0].upper()
        args = tokens[1:]

        if cmd == "WRITE" and len(args) == 2:
            self.write(args[0], int(args[1]))
        elif cmd == "READ" and len(args) == 1:
            self.read(args[0])
        elif cmd == "COUNTVAL" and len(args) == 1:
            self.countval(int(args[0]))
        elif cmd == "CHECKPOINT":
            self.checkpoint()
        elif cmd == "REVERT":
            self.revert()
        elif cmd == "SAVE" and len(args) == 1:
            self.save(args[0])
        elif cmd == "LOAD" and len(args) == 1:
            self.load(args[0])
        else:
            print("Invalid command")

def main():
    store = CountingStore()
    for line in sys.stdin:
        store.process_command(line)
        # print(line)
        print(store.checkpoints)
        print(store.store)


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


main()


