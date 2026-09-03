# AWS Step Functions Data Flow (JSONata)

AWS Step Functions recently introduced **JSONata** as a powerful alternative to JSONPath for data transformation. This makes manipulating input and output states much easier and eliminates the need for complex `ResultPath`, `InputPath`, and `Parameters` configurations.

By setting `"QueryLanguage": "JSONata"` at the state machine or individual state level, you gain access to new fields (`Arguments`, `Output`, `Assign`) and the `$states` reserved variable.

## The `$states` Reserved Variable

When using JSONata, Step Functions exposes the execution environment through the `$states` variable. Here are the different states of input/output you will encounter:

| Variable | Description | When to use it |
| :--- | :--- | :--- |
| **`$states.input`** | The raw input payload received by the current state. | Use in `Arguments` to pass specific input data to a Lambda or service, or in `Output`/`Assign`. |
| **`$states.result`** | The raw output returned by the state's resource (e.g., Lambda payload). | Use in `Output` to shape the data before it goes to the next state. |
| **`$states.errorOutput`** | The error object containing error details. | Use in `Catch` blocks to extract error messages or codes. |
| **`$states.context`** | The execution context (e.g., Execution ID, AWS account info). | Use to pass execution metadata to a task. |

---

## 1. Passing Extra Data Alongside Input (`Arguments`)

If you want to construct a payload that includes your original input data *plus* some extra data, you use the **`Arguments`** field (which replaces the old `Parameters` field). 

Expressions are evaluated inside `{% %}` blocks.

### Example: Adding extra fields to the input
In your scenario, you needed to add `heat_id` to the payload. Here is how you can pass the entire input, plus the extracted `heat_id`, and a static value:

```json
"MyTaskState": {
  "Type": "Task",
  "Resource": "arn:aws:states:::lambda:invoke",
  "QueryLanguage": "JSONata",
  "Arguments": {
    "original_data": "{% $states.input %}",
    "heat_id": "{% $states.input.detail.heat_id %}",
    "extra_static_value": "My Custom Value"
  }
}
```

### Advanced: Merging Extra Data into the Input Root
If you want to append `heat_id` directly to the root of the input object instead of nesting it under `original_data`, you can use JSONata's built-in `$merge` function:

```json
"MyTaskState": {
  "Type": "Task",
  "Resource": "arn:aws:states:::lambda:invoke",
  "QueryLanguage": "JSONata",
  "Arguments": "{% $merge([$states.input, {'heat_id': $states.input.detail.heat_id}]) %}"
}
```

---

## 2. Shaping the Output for the Next State (`Output`)

After a task executes, the raw result is stored in `$states.result`. You use the **`Output`** field to dictate exactly what the next state will receive as its input. 

If you do not specify `Output`, the next state receives whatever was in `$states.result`.

### Example: Combining Task Result with Original Input
A very common pattern is keeping the original input but attaching the task's result to it (previously done via `ResultPath` in JSONPath).

```json
"ProcessData": {
  "Type": "Task",
  "Resource": "arn:aws:states:::lambda:invoke",
  "QueryLanguage": "JSONata",
  "Arguments": {
    "id": "{% $states.input.id %}"
  },
  "Output": {
    "original_input": "{% $states.input %}",
    "task_result": "{% $states.result.Payload %}",
    "status": "SUCCESS"
  }
}
```

---

## 3. Storing Data Globally (`Assign`)

JSONata in Step Functions introduces **Variables**. Using the **`Assign`** field, you can store data in variables that persist throughout the entire execution. This means you no longer have to endlessly pass data from state to state just because a state at the very end of the workflow needs it.

### Example: Saving values for later

```json
"CalculateTotal": {
  "Type": "Pass",
  "QueryLanguage": "JSONata",
  "Assign": {
    "heat_id": "{% $states.input.detail.heat_id %}",
    "orderId": "{% $states.input.order_id %}"
  },
  "Next": "SomeOtherState"
}
```

Later in your workflow, in any state, you can access those variables by simply prefixing them with a `$` sign:

```json
"FinalState": {
  "Type": "Pass",
  "QueryLanguage": "JSONata",
  "Output": {
    "message": "{% 'Processed order ' & $orderId & ' with heat ' & $heat_id %}"
  }
}
```

---

## 4. Simplified Choice States

When using JSONata, `Choice` states become much more intuitive. Instead of using verbose operators like `StringEquals` or `NumericGreaterThanPath`, you evaluate conditions natively using boolean JSONata expressions wrapped in `{% %}`.

### Example: Simple Choice Condition
Branch logic based on fields within `$states.input`.

```json
"CheckStatus": {
  "Type": "Choice",
  "QueryLanguage": "JSONata",
  "Choices": [
    {
      "Condition": "{% $states.input.type = 'Goal' %}",
      "Next": "ProcessGoal"
    },
    {
      "Condition": "{% $states.input.type = 'Assist' %}",
      "Next": "ProcessAssist"
    }
  ],
  "Default": "UnknownType"
}
```

### Example: Complex Logic in a Single Condition
You can use `and`, `or`, and mathematical evaluations directly within the `Condition` expression.

```json
"CheckComplexStatus": {
  "Type": "Choice",
  "QueryLanguage": "JSONata",
  "Choices": [
    {
      "Condition": "{% $states.input.status = 'active' and $states.input.score >= 80 %}",
      "Next": "HighScoringActive"
    },
    {
      "Condition": "{% $states.input.status = 'inactive' or $states.input.is_archived = true %}",
      "Next": "Cleanup"
    }
  ],
  "Default": "DoNothing"
}
```

### Example: Checking a Saved Variable
You can evaluate Choice paths based on previously saved variables using the `Assign` feature:

```json
"CheckVariable": {
  "Type": "Choice",
  "QueryLanguage": "JSONata",
  "Choices": [
    {
      "Condition": "{% $heat_id != null %}",
      "Next": "HasHeatId"
    }
  ],
  "Default": "NoHeatId"
}
```
