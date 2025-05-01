import heapq
from collections import deque

def schedule_tasks(tasks, cooldown):
    if not tasks:
        return 0
    
    # Step 1: Count task frequencies
    freq_map = {}
    for task in tasks:
        freq_map[task] = freq_map.get(task, 0) + 1
    
    # Step 2: Initialize max-heap (using negative frequencies for max-heap in Python)
    max_heap = []
    for task, freq in freq_map.items():
        heapq.heappush(max_heap, (-freq, task))
    
    time = 0
    cooldown_queue = deque()  # Stores (time_available, task, remaining_freq)
    
    # Step 3: Scheduling loop
    while max_heap or cooldown_queue:
        # Check if any tasks are coming off cooldown
        while cooldown_queue and cooldown_queue[0][0] <= time:
            _, task, remaining_freq = cooldown_queue.popleft()
            heapq.heappush(max_heap, (-remaining_freq, task))
        
        if max_heap:
            # Schedule the task with highest remaining frequency
            neg_freq, task = heapq.heappop(max_heap)
            remaining_freq = -neg_freq - 1  # Decrement frequency
            
            if remaining_freq > 0:
                # Put back into cooldown queue
                cooldown_queue.append((time + cooldown + 1, task, remaining_freq))
            
            time += 1
        else:
            # No tasks available - jump to next available time
            if cooldown_queue:
                time = cooldown_queue[0][0]
    
    return time