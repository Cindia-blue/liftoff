import unittest
from task_scheduler import schedule_tasks  # Assuming your code is in task_scheduler.py

class TestTaskScheduler(unittest.TestCase):
    def test_standard_case_with_cooldown(self):
        tasks = ['a','a','a','b','b','b']
        cooldown = 2
        self.assertEqual(schedule_tasks(tasks, cooldown), 8)
    
    def test_no_cooldown_needed(self):
        tasks = ['a','b','c','a','b','c']
        cooldown = 0
        self.assertEqual(schedule_tasks(tasks, cooldown), 6)
    
    def test_all_tasks_identical_with_cooldown(self):
        tasks = ['a','a','a','a']
        cooldown = 3
        self.assertEqual(schedule_tasks(tasks, cooldown), 13)
    
    def test_single_task_with_cooldown(self):
        tasks = ['a']
        cooldown = 5
        self.assertEqual(schedule_tasks(tasks, cooldown), 1)
    
    def test_empty_task_list(self):
        tasks = []
        cooldown = 2
        self.assertEqual(schedule_tasks(tasks, cooldown), 0)
    
    def test_tasks_with_different_frequencies(self):
        tasks = ['a','a','b','c']
        cooldown = 2
        self.assertEqual(schedule_tasks(tasks, cooldown), 3)
    
    def test_large_input_with_minimal_cooldown(self):
        tasks = ['a'] * 1000 + ['b'] * 999
        cooldown = 1
        self.assertEqual(schedule_tasks(tasks, cooldown), 1999)
    
    def test_randomized_input(self):
        import random
        random.seed(42)
        tasks = [random.choice(['a','b','c','d']) for _ in range(1000)]
        cooldown = 3
        # We don't know exact output but should complete without error
        result = schedule_tasks(tasks, cooldown)
        self.assertGreaterEqual(result, len(tasks))
    
    def test_cooldown_larger_than_task_count(self):
        tasks = ['a','b','c']
        cooldown = 5
        self.assertEqual(schedule_tasks(tasks, cooldown), 3)
    
    def test_multiple_tasks_max_cooldown(self):
        tasks = ['a','a','a','b','b','b','c','c','c','d','e']
        cooldown = 100
        self.assertEqual(schedule_tasks(tasks, cooldown), 205)

if __name__ == '__main__':
    unittest.main()