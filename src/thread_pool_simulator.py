"""Thread pool simulator for educational purposes."""

from __future__ import annotations

import argparse
import queue
import random
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class TaskState(str, Enum):
    WAITING = "waiting"
    RUNNING = "running"
    DONE = "done"


@dataclass
class Task:
    task_id: int
    duration_s: float
    state: TaskState = TaskState.WAITING
    started_at: Optional[float] = None
    finished_at: Optional[float] = None

    def run(self) -> None:
        self.state = TaskState.RUNNING
        self.started_at = time.time()
        time.sleep(self.duration_s)
        self.finished_at = time.time()
        self.state = TaskState.DONE


@dataclass
class Worker:
    worker_id: int
    current_task: Optional[int] = None
    completed: int = 0
    timeline: List[str] = field(default_factory=list)

    def log(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.timeline.append(f"[{timestamp}] {message}")


class ThreadPoolSimulator:
    def __init__(self, worker_count: int, tasks: List[Task]) -> None:
        self.worker_count = worker_count
        self.tasks = tasks
        self.task_queue: "queue.Queue[Task]" = queue.Queue()
        self.workers: Dict[int, Worker] = {
            worker_id: Worker(worker_id=worker_id)
            for worker_id in range(1, worker_count + 1)
        }
        self._threads: List[threading.Thread] = []
        self._lock = threading.Lock()

    def load_tasks(self) -> None:
        for task in self.tasks:
            self.task_queue.put(task)

    def _worker_loop(self, worker: Worker) -> None:
        worker.log("started")
        while True:
            try:
                task = self.task_queue.get(timeout=0.2)
            except queue.Empty:
                break
            with self._lock:
                worker.current_task = task.task_id
                worker.log(f"picked task {task.task_id} ({task.duration_s:.2f}s)")
            task.run()
            with self._lock:
                worker.completed += 1
                worker.log(f"finished task {task.task_id}")
                worker.current_task = None
            self.task_queue.task_done()
        worker.log("idle - no more tasks")

    def run(self) -> None:
        self.load_tasks()
        for worker in self.workers.values():
            thread = threading.Thread(target=self._worker_loop, args=(worker,))
            thread.start()
            self._threads.append(thread)
        for thread in self._threads:
            thread.join()

    def summary(self) -> str:
        lines = ["\n=== Simulation Summary ==="]
        total_duration = 0.0
        for task in self.tasks:
            if task.started_at is None or task.finished_at is None:
                continue
            total_duration += task.finished_at - task.started_at
        avg_duration = total_duration / len(self.tasks) if self.tasks else 0.0
        lines.append(f"Workers: {self.worker_count}")
        lines.append(f"Tasks: {len(self.tasks)}")
        lines.append(f"Average task runtime: {avg_duration:.2f}s")
        for worker in self.workers.values():
            lines.append(
                f"Worker {worker.worker_id}: completed {worker.completed} tasks"
            )
        lines.append("==========================\n")
        return "\n".join(lines)

    def detailed_report(self) -> str:
        lines = ["\n=== Worker Timelines ==="]
        for worker in self.workers.values():
            lines.append(f"\nWorker {worker.worker_id} timeline:")
            lines.extend(f"  {entry}" for entry in worker.timeline)
        lines.append("========================\n")
        return "\n".join(lines)


def build_tasks(task_count: int, min_s: float, max_s: float, seed: Optional[int]) -> List[Task]:
    rng = random.Random(seed)
    tasks = []
    for task_id in range(1, task_count + 1):
        duration = rng.uniform(min_s, max_s)
        tasks.append(Task(task_id=task_id, duration_s=duration))
    return tasks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulate a thread pool executing tasks.",
    )
    parser.add_argument("--workers", type=int, default=4, help="Number of workers")
    parser.add_argument("--tasks", type=int, default=10, help="Number of tasks")
    parser.add_argument(
        "--min", dest="min_s", type=float, default=0.5, help="Min task duration"
    )
    parser.add_argument(
        "--max", dest="max_s", type=float, default=2.0, help="Max task duration"
    )
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument(
        "--report", action="store_true", help="Show worker timeline report"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.workers <= 0:
        raise SystemExit("Workers must be positive.")
    if args.tasks < 0:
        raise SystemExit("Tasks cannot be negative.")
    if args.min_s < 0 or args.max_s < 0:
        raise SystemExit("Task durations must be non-negative.")
    if args.min_s > args.max_s:
        raise SystemExit("Min duration cannot exceed max duration.")

    tasks = build_tasks(args.tasks, args.min_s, args.max_s, args.seed)
    simulator = ThreadPoolSimulator(worker_count=args.workers, tasks=tasks)
    print("Starting simulation...")
    simulator.run()
    print(simulator.summary())
    if args.report:
        print(simulator.detailed_report())


if __name__ == "__main__":
    main()
