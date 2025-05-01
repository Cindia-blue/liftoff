from sortedcontainers import SortedList
from collections import deque

class Solution:
    def maxTaskAssign(self, tasks: List[int], workers: List[int], pills: int, strength: int) -> int:
        """
        Time Complexity: O(min⁡(n,m)⋅log⁡2(min⁡(n,m)))
Space Complexity: O(min⁡(n,m))
        """
        tasks.sort()
        workers.sort()
        
        def check(ans):
            task_slice = list(reversed(tasks[-ans:]))  # hardest k tasks
            worker_slice = deque(workers[-ans:])       # strongest k workers

            remain_pills = pills

            for task in task_slice:
                if worker_slice and worker_slice[-1] >= task:
                    worker_slice.pop()
                elif worker_slice and worker_slice[0] + 2 * strength >= task and remain_pills >= 2:
                    worker_slice.popleft()
                    remain_pills -= 2
                elif worker_slice and worker_slice[0] + strength >= task and remain_pills >= 1:
                    worker_slice.popleft()
                    remain_pills -= 1
                else:
                    return False
            return True

            
        
        left, right = 0, min(len(workers), len(tasks)) + 1
        while left + 1 < right:
            mid = (left + right)//2
            if check(mid):
                left = mid
            else:
                right = mid

        return left

