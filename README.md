# Gremlin Migration Tool

This tool replicates health checks, external-integrations, and scenarios between Gremlin teams. It can be used to migrate or backup configuration from one (or more) source team(s) to a destination team on the Gremlin platform.

## Features

- **Migrate Health Checks:** Copy health checks from one or more source teams to a destination team.
- **Migrate Scenarios:** Replicate scenarios, updating any referenced health check IDs.
- **External Integrations:** Copy external integrations from the source team to the destination team.
- **Optional Cleanup:** Delete existing health checks and scenarios in the destination team before migration.

## Prerequisites

- Python 3.6 or higher.
- Valid API keys for both the source and destination Gremlin accounts.

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/yourusername/gremlin-migration.git
   cd gremlin-migration
   ```

2. **Create and activate a virtual environment:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

## Usage

The script can be run directly via the command line. You can supply API keys either via command-line arguments or through environment variables:

- `GREMLIN_SOURCE_API_KEY` for the source API key.
- `GREMLIN_DEST_API_KEY` for the destination API key.

### Command-line Arguments

```bash
python migrate.py \
    --source-team-ids <source_team_id1> <source_team_id2> ... \
    --target-team-id <destination_team_id> \
    [--source-api-key <source_api_key>] \
    [--dest-api-key <destination_api_key>] \
    [--delete-health-checks] \
    [--delete-scenarios]
```

For example:

```bash
python migrate.py \
    --source-team-ids f379c5b5-6736-46a7-b9c5-b56736e6a7fb \
    --target-team-id d531169c-4458-4b47-b116-9c44580b471a \
    --delete-health-checks \
    --delete-scenarios
```

### Help Message

Running the script without any arguments displays the help message:

```bash
python migrate.py -h
```

Output:

```
usage: migrate.py [-h] [--source-api-key SOURCE_API_KEY] [--dest-api-key DEST_API_KEY]
                  --source-team-ids SOURCE_TEAM_IDS [SOURCE_TEAM_IDS ...]
                  --target-team-id TARGET_TEAM_ID [--delete-health-checks]
                  [--delete-scenarios]

Gremlin Health Checks, Integrations, and Scenarios Replicator

options:
  -h, --help            show this help message and exit
  --source-api-key SOURCE_API_KEY
                        Source API key (or set GREMLIN_SOURCE_API_KEY env variable)
  --dest-api-key DEST_API_KEY
                        Destination API key (or set GREMLIN_DEST_API_KEY env variable)
  --source-team-ids SOURCE_TEAM_IDS [SOURCE_TEAM_IDS ...]
                        One or more source team IDs (space-separated)
  --target-team-id TARGET_TEAM_ID
                        Destination team ID
  --delete-health-checks
                        Delete existing health checks in destination team
  --delete-scenarios    Delete existing scenarios in destination team
```

## Local Development

1. **Clone and create a virtual environment:**

   ```bash
   git clone https://github.com/yourusername/gremlin-migration.git
   cd gremlin-migration
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Migration:**

   ```bash
   python migrate.py --source-team-ids <source_team_id> --target-team-id <destination_team_id> [--delete-health-checks] [--delete-scenarios]
   ```

## Environment Variables

To avoid entering your API keys each time, set the following environment variables in your shell or add them to your virtual environment's activation script:

- On macOS/Linux:

  ```bash
  export GREMLIN_SOURCE_API_KEY="your_source_api_key"
  export GREMLIN_DEST_API_KEY="your_destination_api_key"
  ```

- On Windows (Command Prompt):

  ```batch
  set GREMLIN_SOURCE_API_KEY=your_source_api_key
  set GREMLIN_DEST_API_KEY=your_destination_api_key
  ```

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
