# AWS Migration Baseline - Student App

This document finalizes the migration proposal into an execution baseline with concrete defaults.
It is intentionally opinionated so implementation can start immediately.

## 1) Non-Functional Baseline (Final Defaults)

### Traffic and scale assumptions
- Peak concurrent users: 1,500
- Peak API RPS: 250 sustained, 500 burst for 5 minutes
- Chatbot peak: 40 RPS (request + tool calls)
- Daily active users: 8,000 to 12,000

### Availability and reliability targets
- Production availability target: 99.9%
- API latency target: p95 < 450 ms (non-chat routes)
- Chat route latency target: p95 < 2.5 s end-to-end
- RTO: 60 minutes
- RPO: 15 minutes

### Security and compliance defaults
- Compliance baseline: GDPR-aligned handling for student personal data
- Encryption at rest: mandatory for RDS, S3, and Secrets Manager (KMS-managed keys)
- Encryption in transit: TLS 1.2+ everywhere
- Secrets rotation: 90 days for app secrets; DB credentials via managed rotation where supported
- Audit retention: 365 days in hot storage, 2 years archive

### Cost baseline
- Initial monthly target: 1,500-3,500 EUR for non-prod + prod combined
- Cost guardrails:
  - CloudWatch budget alarms at 60%, 80%, 100%
  - Bedrock spend alarm at 70% of monthly chatbot budget
  - Tag-based cost allocation per environment and service

### Region and DR
- Primary region: eu-central-1
- Production topology: Multi-AZ within single region
- DR posture phase 1: snapshot and backup restore to secondary region on incident
- DR posture phase 2 (optional): warm standby in eu-west-1

## 2) Service and Runtime Decisions

### Compute
- Start with ECS Fargate for the current FastAPI backend as one service.
- Extract Lambda workloads only for:
  - Scheduled jobs from `backend/workers/tasks.py`
  - Notification fan-out processors
  - Bedrock chat orchestration adapter (after tool contracts are introduced)

### Data
- Keep one PostgreSQL database (Amazon RDS PostgreSQL) in phase 1.
- Use RDS Proxy for ECS and Lambda connectivity.
- Keep Alembic migrations, but execute via dedicated migration job in pipeline.

### API and edge
- Use API Gateway HTTP API.
- Keep one gateway with path-based domains (`/auth`, `/chat`, `/student`, `/professor`, `/admin`, `/notifications`).
- Serve frontend with CloudFront + S3.

### Storage
- Buckets:
  - `studentapp-frontend-<env>`
  - `studentapp-artifacts-<env>`
  - `studentapp-uploads-<env>` (reserved for future uploads)

## 3) Auth Decision (Final)

- Adopt Amazon Cognito, but not in phase 1.
- Phased auth migration:
  1. Phase 1: Keep current JWT auth in backend (`backend/services/auth_service.py` and `backend/middleware/auth_middleware.py`).
  2. Phase 2: Introduce Cognito user pool and API Gateway JWT authorizer.
  3. Phase 3: Backend accepts both legacy JWT and Cognito JWT.
  4. Phase 4: Frontend login moves fully to Cognito.
  5. Phase 5: Remove legacy JWT issuance endpoints.

Reasoning: fastest low-risk AWS cutover while preserving current behavior.

## 4) IaC and Deployment Decision (Final)

### IaC
- Use Terraform as the single IaC framework.
- Repository layout recommendation:
  - `infra/environments/dev`
  - `infra/environments/staging`
  - `infra/environments/prod`
  - `infra/modules/*` for reusable components

### Pipeline
- CI/CD stages:
  1. Lint and tests (frontend + backend)
  2. Build frontend assets
  3. Build backend image and push to ECR
  4. Run Terraform plan/apply (environment-gated)
  5. Run Alembic migration task
  6. Deploy ECS service
  7. Upload frontend to S3 and invalidate CloudFront

### Secrets and config policy
- Secrets Manager for secrets (`DATABASE_URL`, JWT secrets, SendGrid/SES keys, Bedrock keys if needed).
- SSM Parameter Store for non-secret config.
- No `.env` in production runtime images.

## 5) Approved Migration Order and Exit Criteria

## Phase A - Foundation
- Build VPC, subnets, NAT, SGs, IAM roles, ECR, RDS, CloudWatch.
- Exit criteria:
  - RDS reachable from private subnets
  - Logs/metrics visible in CloudWatch

## Phase B - Monolith Lift-and-Shift
- Deploy FastAPI monolith to ECS Fargate.
- Deploy React app to S3 + CloudFront.
- Point app to RDS and validate all critical flows.
- Exit criteria:
  - Student booking via chat works end-to-end
  - Professor booking management works
  - Error rate < 1% over 72 hours

## Phase C - Operational Hardening
- Remove migrate-on-startup behavior from runtime path.
- Add migration job in pipeline.
- Add RDS Proxy, alarms, tracing, dashboard, on-call runbook.
- Exit criteria:
  - Zero manual DB changes
  - Alert coverage for API, DB, and queue failures

## Phase D - Async and Scheduling Externalization
- Move `workers/tasks.py` logic to EventBridge + Lambda (or ECS scheduled tasks where needed).
- Introduce SNS/SQS for notification fan-out.
- Exit criteria:
  - No manual `/admin/scheduler/run/*` dependency for production operations

## Phase E - Chat Modernization
- Replace internals of rule-based chat path with Bedrock orchestrator.
- Preserve `conversations` persistence and existing route contract (`/chat`).
- Exit criteria:
  - Same booking success rate as baseline
  - Cost and latency within defined budgets/SLOs

## Phase F - Auth Modernization
- Migrate frontend and gateway auth to Cognito.
- Keep dual-token support during cutover, then retire legacy JWT issuance.
- Exit criteria:
  - 100% production traffic authenticated by Cognito tokens

## Phase G - Decommission Legacy Host
- Shut down old host only after:
  - 14 days stable in AWS
  - No unresolved Sev1/Sev2 incidents
  - Backup restore test passed

## 6) Known Refactor Prerequisites

- Some domain logic still lives in route files (`backend/routers/student.py`, `backend/routers/professor.py`, `backend/routers/admin.py`).
  - Move critical business logic deeper into services before major decomposition.
- `backend/services/chat_service.py` is coupled to multiple services.
  - Introduce explicit tool interfaces before Bedrock migration.
- Login rate limiting is in-memory in `backend/routers/auth.py`.
  - Move to distributed store (Redis/ElastiCache) before horizontal scaling.

## 7) Immediate Next Actions

1. Create Terraform scaffolding for networking, ECS, RDS, S3/CloudFront.
2. Add backend Dockerfile and ECS task definition inputs.
3. Prepare migration pipeline with dedicated Alembic job.
4. Create CloudWatch dashboards and critical alarms before go-live.
