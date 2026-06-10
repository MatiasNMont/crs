# Insurance Platform DynamoDB Test Case

This walkthrough uses the Terraform project `aws-reference-example`, a serverless insurance platform for web and mobile channels.

The architecture includes Cognito, CloudFront, S3, WAF, API Gateway, Lambda, Step Functions, DynamoDB, EventBridge, SQS, SNS, KMS, Secrets Manager, CloudWatch, and X-Ray.

## Scenario

The platform stores policies, payments, claims, debts, and user profiles in DynamoDB tables created by `aws_dynamodb_table.domain` in `data.tf`.

The question is:

> What is affected if I delete the domain DynamoDB tables?

## Initialize CRS

```powershell
cd aws-reference-example
crs init .
```

Measured reference graph:

- Terraform files: 11
- CRS nodes: 96
- CRS relationships: 151

`crs init` also installs the CRS-first rules for Codex and Claude Code.

## Find the Component

```powershell
crs search . dynamodb
```

Expected canonical node:

```text
root::aws_dynamodb_table.domain (resource, data, security) - data.tf:1
```

## Analyze Impact

```powershell
crs ask . "What is affected if I delete the domain DynamoDB tables?" --json --detail summary
```

CRS resolves the `impact` intent and reports:

- Focus node: `root::aws_dynamodb_table.domain`
- Direct dependency: `root::aws_kms_key.main`
- Depth 1: Lambda IAM policy document and feature Lambda functions
- Depth 2: Lambda IAM role policy, API Gateway integration/permissions, Step Functions policy and state machine
- Depth 3: API deployment, Step Functions IAM role policy, state-machine output, and workflow-start policy

The result contains 11 downstream affected nodes. Functionally, deleting the tables breaks policy lookup, payment persistence, claim registration, debt queries, and user-profile storage.

## Analyze Failure

```powershell
crs failure . root::aws_dynamodb_table.domain --depth 3
```

Review data-loss and persistence risks, KMS access, Lambda environment configuration, IAM permissions, API failures, workflow behavior, point-in-time recovery, and restoration procedures.

## Validate a Terraform Change

After editing `data.tf`:

```powershell
crs preflight . --max-affected 10
terraform plan
```

CRS provides structural source impact. `terraform plan` remains authoritative for replacements, provider behavior, and deployed-state differences.

## Disable CRS for a Control Test

```powershell
crs disable . --remove-memory
```

Start a new agent session and ask the same question to compare a no-CRS workflow.
