# Atlas Backend Cleanup Plan

## ✅ Phase 1 Complete: Update References 

### What Was Updated:
- ✅ `investigation_dashboard.py` - Now uses `investigate_alert_simple` 
- ✅ `endpoints/investigation_endpoints.py` - Removed ADK approach, only uses simple service
- ✅ `e2etest_investigation.py` - Updated to use `investigate_alert_simple`
- ✅ `e2etest_minimal_agent_integration.py` - Updated to use `investigate_alert_simple`
- ✅ `scripts/test_tracing.py` - Updated to use `investigate_alert_simple`
- ✅ Removed configuration complexity from endpoints - always uses simple approach
- ✅ Cleaned up commented code and unused imports
- ✅ **Removed Vertex AI deployment** from `Makefile` - no longer needed since minimal_working_agent runs locally

### Results:
- All files now consistently use `investigation_service_simple`
- No more conditional logic based on `INVESTIGATION_APPROACH` in endpoints
- Codebase is now simpler and easier to understand
- All e2e tests will use the working minimal agent approach
- **Simplified deployment**: Only need `deploy-api` (backend API container) + `deploy-web` + `deploy-monitor`

### Architecture Insight: ✅ **No Vertex AI Deployment Needed**
The `minimal_working_agent`:
- Runs **locally within** the backend API container 
- Uses `InMemorySessionService` and `ADK Runner` locally
- Only calls Vertex AI for **model inference** (not agent hosting)
- Call chain: `Frontend → Backend API → investigation_service_simple → minimal_working_agent (local)`

## Current Architecture Status

### ✅ ACTIVE FILES (Keep)
- `investigation_service_simple.py` - Current default service
- `minimal_working_agent.py` - Working agent implementation  
- `endpoints/investigation_endpoints.py` - Now simplified to only use simple approach

### ❌ LEGACY FILES (Ready for Removal in Phase 2)
- `investigation_service.py` - Old ADK multi-agent approach (NO LONGER REFERENCED)
- `root_agent.py` - Complex 5-agent coordination (NO LONGER REFERENCED) 
- `deployment/deploy.py` - Deploys the unused ADK approach (NO LONGER REFERENCED)

## Next Steps - Phase 2: Remove Legacy Files  

Ready to proceed with Phase 2:
1. Delete `investigation_service.py`
2. Delete `root_agent.py` 
3. Delete `deployment/deploy.py` (or update to deploy minimal_working_agent if needed)

These files are now safe to delete since no active code references them.

## Benefits Achieved in Phase 1
- ✅ Eliminated confusion about which service to use
- ✅ All tests now use the proven working approach
- ✅ Simplified endpoint logic (no more conditional branching)
- ✅ Consistent codebase focused on `minimal_working_agent` + `investigation_service_simple`

## Configuration Impact
- `INVESTIGATION_APPROACH` config can remain for backward compatibility in tests
- Main application no longer uses this configuration
- All endpoints default to simple approach regardless of config setting

## Cleanup Steps

### Phase 3: Clean up Related Files
1. Remove unused agent files if they're only referenced by the deleted root_agent:
   - `agents/research_agent.py`
   - `agents/data_agent.py` 
   - `agents/analysis_agent.py`
   - `agents/report_agent.py`
2. Remove coordination tools that were ADK-specific
3. Update any remaining imports

## Benefits
- Simpler codebase focused on the working approach
- Reduced confusion about which service to use
- Faster development without maintaining two approaches
- Cleaner deployment story

## Risks
- If anyone was using the ADK approach, they'll need to switch
- Lose the multi-agent coordination capability (though it wasn't working reliably)
- Need to ensure all tests pass after cleanup

## Configuration Impact
- `INVESTIGATION_APPROACH` config can be simplified to always use "simple"
- Remove ADK-related environment variables if not needed elsewhere
- Update documentation to reflect the single approach 