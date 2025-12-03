# Chopsticks GitHub Actions Workflows

## Functional Tests

The `functional-tests.yml` workflow runs comprehensive S3 stress tests on every pull request to validate that the framework is working correctly.

### What It Tests

1. **MicroCeph Setup**: Deploys a single-node MicroCeph cluster with 3 OSDs using loop devices
2. **S3 Configuration**: Creates S3 user, configures RGW endpoint, and sets up test bucket
3. **S3 Operations**: Runs 2-minute stress test with:
   - 3 concurrent users
   - 10MB object size
   - Upload, download, and delete operations
4. **Metrics Collection**: Validates that metrics are collected and exported
5. **Success Validation**: Ensures 100% success rate and minimum operation count

### Workflow Triggers

- **Pull Requests**: Runs on all PRs targeting `main`
- **Push to main**: Runs after merging
- **Manual**: Can be triggered manually via GitHub Actions UI

### Test Duration

- **Total Runtime**: ~15-20 minutes
  - MicroCeph setup: ~5 minutes
  - Test execution: 2 minutes
  - Cleanup and validation: ~1 minute

### Artifacts

The workflow uploads test artifacts that persist for 30 days:
- HTML test report (`chopsticks-ci-report.html`)
- Metrics files (JSON, CSV, JSONL)
- Locust statistics CSV files

### Running Locally

You can run the same functional test locally using the provided script:

```bash
# With default settings (2 minutes, 10MB objects, 3 users)
./scripts/run-functional-test.sh

# With custom settings
TEST_DURATION=5m LARGE_OBJECT_SIZE=50 TEST_USERS=5 ./scripts/run-functional-test.sh
```

**Prerequisites:**
- MicroCeph installed and running
- RGW enabled
- `uv`, `jq`, and `s5cmd` installed

### Validation Criteria

The test passes if:
1. ✅ Success rate is 100%
2. ✅ At least 10 operations completed
3. ✅ Metrics files are generated correctly
4. ✅ No exceptions or errors occurred

### Failure Scenarios

The test fails if:
- ❌ MicroCeph fails to start
- ❌ RGW endpoint is not accessible
- ❌ Any S3 operation fails
- ❌ Success rate < 100%
- ❌ Metrics not exported properly

### Future Enhancements

Planned additions:
- [ ] RBD workload tests
- [ ] Multi-scenario tests
- [ ] Performance regression detection
- [ ] Integration with different S3 client drivers
- [ ] Grafana dashboard validation
