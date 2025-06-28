# TokenScript compliance suite
This repository contains a set of tests which can be used to verify the compliance of a TokenScript interpreter with the TokenScript specification.

Each test is a json file containing a set of test cases. Each test case has the following structure:

```json
{
    "name": "test addition",
    "input": "4+{x}",
    "expectedOutput": "7",
    "expectedOutputType": "Number",
    "context": {
       "x": 3
    }
}
```

Every interpreter implementation should have a cli method called `evaluate_standard_compliance` which takes a path to a directory containing the tests, reads it recursively and executes them. The method should return a report in the following format:`

```json
{
    "passed": 10,
    "failed": 2,
    "results": [
        {
            "status": "passed",
            "path": "tests/addition.json",
            "name": "test addition",
            "actualOutput": "6",
            "actualOutputType": "Number",
            "expectedOutput": "6",
            "expectedOutputType": "Number",
            "error": null
        }
    ]
}
```

A test is considered passed if the actual output matches the expected output and the actual output type matches the expected output type. For every test the actual output and actual output type should be included in the report.

## Notes
- Floating numbers should be rounded to 15 decimal places. For example, `0.1 + 0.2` should be `0.3` and not `0.30000000000000004`.
