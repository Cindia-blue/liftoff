# dominoes_simulation.py

class Solution:
    def pushDominoes(self, dominoes: str) -> str:
        arr = list(dominoes)
        n = len(arr)
        forces = []

        # Step 1: Record all non-dot positions
        for i, c in enumerate(arr):
            if c != '.':
                forces.append((i, c))

        # Step 2: Add virtual boundaries for left and right edges
        forces = [(-1, 'L')] + forces + [(n, 'R')]

        # Step 3: Process between each pair
        for (i, left), (j, right) in zip(forces, forces[1:]):
            if left == right:
                # Same direction: fill with the same character
                for k in range(i + 1, j):
                    arr[k] = left
            elif left == 'R' and right == 'L':
                # Opposing forces: fill inward symmetrically
                l, r = i + 1, j - 1
                while l < r:
                    arr[l] = 'R'
                    arr[r] = 'L'
                    l += 1
                    r -= 1
                # If l == r, middle stays '.'
            # Else: 'L'...'R', do nothing

        return ''.join(arr)


# Unit tests
if __name__ == "__main__":
    sol = Solution()
    assert sol.pushDominoes(".L.R...LR..L..") == "LL.RR.LLRRLL.."
    assert sol.pushDominoes("RR.L") == "RR.L"
    assert sol.pushDominoes("R...L") == "RR.LL"
    assert sol.pushDominoes("L....") == "LLLLL"
    assert sol.pushDominoes("....R") == "....R"
    assert sol.pushDominoes("L....R") == "L....R"
    print("All tests passed.")
