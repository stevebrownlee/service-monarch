# Monarch Service

## Overview

Monarch is an independent service that is a part of the Learning Platform system that handles migrating tickets from the source group project repositories to each of the student teams' repositories. The Learning Platform API sends a message to a Valkey instance on the **channel_migrate_issue_tickets** channel after repos are created, students are added as collaborators, and Slack messages have been sent.

```py
message = json.dumps({
    'notification_channel': cohort.slack_channel,
    'source_repo': project.client_template_url,
    'all_target_repositories': issue_target_repos
})

valkey_client.publish('channel_migrate_issue_tickets', message)
```

The Monarch service listens for messages on the channel and kicks off issue ticket migration if the source repository has any, otherwise the migration process is skipped.

```py
pubsub = self.valkey_client.pubsub()
pubsub.subscribe('channel_migrate_issue_tickets')

for message in pubsub.listen():
    if message['type'] == 'message':
        data = MigrationData.model_validate_json(message['data'])
        await self.migrate_tickets(data)
```

## System Dependencies

- Python 3.10+
- [Valkey](https://valkey.io/topics/installation/)
- [valkey-py](https://github.com/valkey-io/valkey-py)
- [pipenv](https://pipenv.pypa.io/en/latest/) virtual environment manager

## Service Dependencies

- [requests](https://docs.python-requests.org/en/latest/index.html) for HTTP communication with Github and Slack
- [structlog](https://www.structlog.org/en/stable/index.html) for logging
- [pydantic](https://docs.pydantic.dev/latest/) for data validation
- [prometheus_client](https://prometheus.github.io/client_python/getting-started/three-step-demo/) for metrics
- [tenacity](https://tenacity.readthedocs.io/en/latest/) for HTTP request retrying

## Installation

1. Ensure Valkey is installed on your system by visiting the [Valkey Installation](https://valkey.io/topics/installation/) documentation.
2. Clone the Monarch repository:
    ```sh
    git clone git@github.com:stevebrownlee/service-monarch.git
    cd service-monarch
    ```

3. Install the required Python packages using `pipenv`:
    ```sh
    pipenv install
    ```

4. Start the shell for the project using `pipenv`:
    ```sh
    pipenv shell
    ```
5. Open the project with your code editor.
6. Copy the `.env.template` file as `.env`.
7. Update the `.env` file with the appropriate values as you generate them.
8. Run the service in the terminal
    ```sh
    cd monarch
    python main.py
    ```
    or start the project in debug mode in your code editor.

## Testing Locally with Valkey CLI

To test the Monarch service using `valkey-cli`, follow these steps:

1. Start the Valkey server _(refer back to Valkey site for instructions)_.
2. Open a new terminal and connect to Valkey CLI:
    ```sh
    valkey-cli
    ```
3. Run the **MONITOR** command, which will observe all activity.
4. In a separate terminal, send a test message to verify Valkey is working correctly:
    ```sh
    valkey-cli PUBLISH test-channel "Hello World"
    ```
5. Start the Monarch service in debug mode in VSCode.
6. Publish the following message to Valkey, replacing the source and target repository endpoints:
    ```sh
    valkey-cli PUBLISH channel_migrate_issue_tickets '{ "source_repo": "source-org/source-repo-with-issues", "all_target_repositories": ["target-org/target-repo"], "notification_channel": "C06GHMZB3M3"}'
    ```
7. You can watch both the Valkey terminal window to see the messaging, and the terminal output in VSCode as the tickets are migrated.
8. Review the metrics and public logs:
   - Access the log viewer web interface at: http://localhost:8081/
   - Access the health endpoint at: http://localhost:8081/health
   - Access metrics at: http://localhost:8080/

## Sequence/System Diagram

```mermaid
sequenceDiagram
    title Learning Platform Ticket Migration

    API->>Switchboard: PUBLISH {payload}
    Switchboard->>+Monarch: RECEIVE {payload}
    activate Monarch
        Monarch->>+Github: GET /issues
        Github-->>-Monarch: List<Issue>
        opt If issues exist
            critical [Create issues on target repo]
            loop List of issues
                Monarch->>+Github: POST issue
                Github->>-Monarch: JSON
            end
            Monarch->>Slack: Migration success
            option [Exception]
                Monarch->>Slack: Migration failed
            end
        end
    deactivate Monarch
```

## Deployment

For a detailed description of how the Monarch service is deployed, refer to the [WORKFLOW](./WORKFLOW.md) document.

## Monitoring Production

### Monarch

#### Viewing Logs

You can view logs in two ways:

1. **Web Interface**:
   - Access the log viewer web interface at: http://{domain}:8081/
   - This provides a user-friendly interface to browse, filter, and search logs

2. **Direct Server Access**:
   - `ssh root@monarch.your.domain`
   - `cd /opt/monarch`
   - `docker compose logs -f`

#### Health Check

Monitor the service health status:
- Access the health endpoint at: http://{domain}:8081/health
- Returns a JSON response with status information including:
  - Overall service status (healthy/degraded/unhealthy)
  - Valkey connection status
  - Last message processing time
  - Service uptime

#### Metrics

View Prometheus metrics for monitoring service performance:
- Access metrics at: http://{domain}:8080/
- Available metrics include:
  - Issue migration counts and errors
  - GitHub API rate limit status
  - Message processing times and errors
  - Connection status
  - Circuit breaker states
  - Watchdog statistics

### Valkey

> You will need to clone the [Infrastructure](https://github.com/stevebrownlee/learnops-infrastructure) repo and run `terraform init` and `terraform plan`.

To enable this, modify the inbound rule on the Valkey droplet in the Terraform config file.

```tf
inbound_rule {
 protocol = "tcp"
 port_range = "6379"
 source_addresses = ["0.0.0.0/0", "::/0"]
}
```
1. Run `terraform apply` to apply the changes.
2. Run `valkey-cli -h {your-domain-name} -p 6379` in your local shell.
3. Once connected, run the **MONITOR** command to watch all activity.

## Architecture

For a detailed explanation of the architectural patterns and strategies used in the Monarch service, refer to the [ARCHITECTURE.md](./ARCHITECTURE.md) document.

## License
This project is licensed under the GNU GENERAL PUBLIC LICENSE.
