import sys

name = input("What's your name? ")
print(f"Hello, {name}!")             # goes to stdout
print(f"Debug: got input {name}", file=sys.stderr)  # goes to stderr