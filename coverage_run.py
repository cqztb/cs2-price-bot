"""Измерение покрытия тестами с помощью стандартного модуля trace.

Используется, когда пакет coverage недоступен. Запускает оба набора
тестов и считает долю выполненных строк в основных модулях.
"""

import os
import sys
import glob
import trace
import unittest

TARGETS = ["logic.py", "storage.py", "scheduler.py"]
COVERDIR = "/tmp/work/coverdir"


def run_tests():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for name in ["test_unit", "test_integration"]:
        suite.addTests(loader.loadTestsFromName(name))
    runner = unittest.TextTestRunner(verbosity=0)
    runner.run(suite)


def main():
    os.makedirs(COVERDIR, exist_ok=True)
    tracer = trace.Trace(count=True, trace=False,
                         ignoredirs=[sys.prefix, sys.exec_prefix])
    tracer.runfunc(run_tests)
    results = tracer.results()
    results.write_results(show_missing=True, coverdir=COVERDIR)

    print("\nПокрытие тестами (statement coverage):")
    print("-" * 52)
    total_exec = total_miss = 0
    for target in TARGETS:
        base = os.path.splitext(os.path.basename(target))[0]
        matches = glob.glob(os.path.join(COVERDIR, f"*{base}.cover"))
        if not matches:
            continue
        executed = missed = 0
        for line in open(matches[0], encoding="utf-8"):
            if line.startswith(">>>>>>"):
                missed += 1
            elif line.split(":", 1)[0].strip().isdigit():
                executed += 1
        total = executed + missed
        pct = 100 * executed / total if total else 0
        total_exec += executed
        total_miss += missed
        print(f"{target:<16} строк: {total:>3}  покрыто: {executed:>3}  "
              f"покрытие: {pct:5.1f}%")
    total = total_exec + total_miss
    print("-" * 52)
    print(f"{'ИТОГО':<16} строк: {total:>3}  покрыто: {total_exec:>3}  "
          f"покрытие: {100*total_exec/total:5.1f}%")


if __name__ == "__main__":
    main()
