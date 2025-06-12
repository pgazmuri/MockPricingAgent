"""
IT Environment Knowledge Base

Defines the rules, behaviors, and logging patterns of our fictional IT environment.
This provides context for realistic mock data generation and agent investigation patterns.
"""

from typing import Dict, List, Any
from datetime import datetime, timedelta


class ITEnvironment:
    """Defines the rules and behaviors of our fictional IT environment"""
    
    # Server heartbeat monitoring rules
    MONITORING_RULES = {
        "heartbeat_interval": "5 minutes",
        "heartbeat_timeout": "15 minutes", 
        "heartbeat_source": "SCOM (System Center Operations Manager)",
        "heartbeat_index": "main",
        "heartbeat_sourcetype": "heartbeat"
    }
    
    # Network and connectivity rules
    NETWORK_RULES = {
        "sql_port": 1433,
        "web_ports": [80, 443],
        "rdp_port": 3389,
        "ssh_port": 22,
        "load_balancer_algorithm": "round-robin",
        "firewall_default": "deny"
    }
    
    # Infrastructure naming conventions
    INFRASTRUCTURE = {
        "naming_convention": {
            "web_servers": "WEB-{ENV}-{NUMBER:02d}",    # WEB-PROD-01
            "sql_servers": "SQL-{ENV}-{NUMBER:02d}",     # SQL-PROD-01  
            "app_servers": "APP-{ENV}-{NUMBER:02d}",     # APP-PROD-01
            "load_balancers": "LB-{ENV}-{NUMBER:02d}",   # LB-PROD-01
        },
        "environments": ["DEV", "TEST", "PROD"],
        "datacenters": ["DC1", "DC2"],
        "domains": ["contoso.com", "internal.contoso.com"]
    }
    
    # Splunk logging configuration
    SPLUNK_CONFIG = {
        "indexes": {
            "main": "Infrastructure events, heartbeats, system metrics",
            "app": "Application logs, errors, performance data", 
            "deployment": "CI/CD pipeline logs, deployment events",
            "security": "Authentication, firewall, access events",
            "metrics": "Performance metrics, resource utilization"
        },
        "sourcetypes": {
            "heartbeat": "Server heartbeat events (every 5 min)",
            "application": "Application logs and errors",
            "pipeline": "Deployment pipeline execution logs", 
            "syslog": "System logs from servers",
            "iis": "IIS web server logs",
            "mssql": "SQL Server logs",
            "firewall": "Network firewall logs"
        },
        "common_fields": [
            "_time", "host", "source", "sourcetype", "index",
            "severity", "component", "message", "user", "session_id"
        ]
    }
    
    # Common investigation scenarios and their log patterns
    INVESTIGATION_SCENARIOS = {
        "server_down": {
            "symptoms": ["Missing heartbeats", "Connection timeouts", "Service unavailable"],
            "log_patterns": ["Last heartbeat > 15 minutes ago", "Host not responding", "TCP connection failed"],
            "common_causes": ["Hardware failure", "OS crash", "Network isolation", "Power outage"],
            "splunk_queries": [
                "index=main sourcetype=heartbeat host=SERVER-NAME | stats latest(_time) as last_heartbeat",
                "index=app host=SERVER-NAME earliest=-4h | tail 20",
                "index=deployment host=SERVER-NAME earliest=-24h | search status=*"
            ]
        },
        "deployment_failure": {
            "symptoms": ["Application errors after deployment", "Service degradation", "New error patterns"],
            "log_patterns": ["Deployment completed", "Application startup errors", "Configuration errors"],
            "common_causes": ["Bad deployment", "Configuration mismatch", "Database migration failure"],
            "splunk_queries": [
                "index=deployment pipeline_name=* earliest=-4h | table _time pipeline_name status stage",
                "index=app severity=ERROR earliest=-2h | timechart span=10m count",
                "index=app \"configuration\" OR \"startup\" earliest=-1h"
            ]
        },
        "database_connectivity": {
            "symptoms": ["SQL timeouts", "Connection refused", "Login failures"],
            "log_patterns": ["Connection timeout", "Login failed", "Network error", "Port 1433 unreachable"],
            "common_causes": ["Firewall changes", "SQL service down", "Network issues", "Authentication problems"],
            "splunk_queries": [
                "index=app \"sql\" OR \"database\" OR \"timeout\" earliest=-2h",
                "index=security port=1433 action=deny earliest=-4h",
                "index=main sourcetype=mssql earliest=-1h | search ERROR OR WARN"
            ]
        }
    }
    
    # Deployment pipeline information
    PIPELINE_CONFIG = {
        "common_pipelines": [
            "web-app-pipeline",
            "api-service-pipeline", 
            "database-migration-pipeline",
            "infrastructure-pipeline"
        ],
        "stages": ["build", "test", "security-scan", "deploy", "health-check"],
        "deployment_frequency": "Multiple times per day",
        "rollback_capability": True,
        "health_check_duration": "5 minutes"
    }

    @classmethod
    def get_splunk_context(cls) -> str:
        """Get Splunk-specific context for tools and agents"""
        return f"""
SPLUNK ENVIRONMENT CONTEXT:

Available Indexes:
{chr(10).join([f"- {idx}: {desc}" for idx, desc in cls.SPLUNK_CONFIG["indexes"].items()])}

Common Source Types:
{chr(10).join([f"- {st}: {desc}" for st, desc in cls.SPLUNK_CONFIG["sourcetypes"].items()])}

Server Monitoring:
- Heartbeats: Every {cls.MONITORING_RULES["heartbeat_interval"]} from {cls.MONITORING_RULES["heartbeat_source"]}
- Missing heartbeat timeout: {cls.MONITORING_RULES["heartbeat_timeout"]}
- Heartbeat location: index={cls.MONITORING_RULES["heartbeat_index"]} sourcetype={cls.MONITORING_RULES["heartbeat_sourcetype"]}

Deployment Tracking:
- All deployments logged to index=deployment sourcetype=pipeline
- Stages: {', '.join(cls.PIPELINE_CONFIG["stages"])}
- Health checks run for {cls.PIPELINE_CONFIG["health_check_duration"]} post-deployment

Common Query Patterns:
- Server status: index=main sourcetype=heartbeat host=HOSTNAME | stats latest(_time) as last_seen
- Recent deployments: index=deployment earliest=-4h | table _time pipeline_name status stage
- Application errors: index=app severity=ERROR earliest=-2h | timechart span=10m count
- Database issues: index=app ("sql" OR "database" OR "timeout") earliest=-1h
"""

    @classmethod
    def get_investigation_patterns(cls) -> str:
        """Get common IT investigation patterns"""
        return """
INVESTIGATION PATTERNS:

1. Server Down Investigation:
   - Check last heartbeat time (should be every 5 min)
   - Look for deployment activity 30-60 min before issue
   - Check for hardware/OS errors in system logs
   - Verify network connectivity patterns

2. Application Issues:
   - Check for recent deployments in deployment logs
   - Look for error spikes in application logs
   - Verify database connectivity if data-driven app
   - Check resource utilization (CPU, memory, disk)

3. Database Connectivity:
   - Test SQL port (1433) accessibility in flow logs
   - Check for authentication failures
   - Look for recent firewall changes
   - Verify SQL Server service status

4. Performance Degradation:
   - Compare current metrics to baseline
   - Check for resource exhaustion
   - Look for concurrent load or traffic spikes
   - Review recent configuration changes

Timeline Analysis:
- Always establish a clear timeline of events
- Correlate symptoms with deployments/changes
- Look for patterns across multiple servers
- Check for cascade failures (one server affecting others)
"""

    @classmethod
    def get_server_name_examples(cls) -> List[str]:
        """Get example server names following naming convention"""
        examples = []
        for env in cls.INFRASTRUCTURE["environments"]:
            for i in range(1, 4):  # Generate 3 servers per environment
                examples.extend([
                    cls.INFRASTRUCTURE["naming_convention"]["web_servers"].format(ENV=env, NUMBER=i),
                    cls.INFRASTRUCTURE["naming_convention"]["sql_servers"].format(ENV=env, NUMBER=i),
                    cls.INFRASTRUCTURE["naming_convention"]["app_servers"].format(ENV=env, NUMBER=i)
                ])
        return examples

    @classmethod
    def get_common_splunk_queries(cls) -> Dict[str, List[str]]:
        """Get common Splunk queries by scenario type"""
        return {scenario: details["splunk_queries"] 
                for scenario, details in cls.INVESTIGATION_SCENARIOS.items()}
