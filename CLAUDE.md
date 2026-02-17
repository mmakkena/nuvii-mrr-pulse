# Claude Code Preferences

## Commit Messages

- Do not include "Generated with Claude Code" footer
- Do not include "Co-Authored-By" footer

# Files structure

- Always place the test scripts in tests folder
- Always place startup and other non test related scripts in scripts folder
- Always place any .md or documentation files other than CLAUDE.md in docs folder

## Docker and AWS Deployments

### Architecture Compatibility

- **ALWAYS** build Docker images for the target platform architecture
- When deploying to AWS ECS/Fargate, use `--platform linux/amd64` or buildx
- ECS runs on x86_64 (amd64) architecture by default
- Building on Apple Silicon (ARM64) without platform specification will cause "exec format error"
- Before pushing images to ECR, verify architecture compatibility:
  ```bash
  docker buildx create --use --name multiplatform-builder
  docker buildx build --platform linux/amd64 -t <image> --push .
  ```
- After deployment, check ECS task logs for architecture-related errors like:
  - "exec format error"
  - "cannot execute binary file"
  - Exit code 255 without clear reason

before deploying make sure local build and run works


# Testing
when performing any testing use realistic data but always use @yopmail.com domain so that emails dont reach any real person

# auto accept
always proceed for commands like aws logs ,aws ecs describe etc that are read only in nature 
