# Dartlog - Version 1.0.0

Welcome to the **first release** of Dartlog! 🎉 Dartlog is a Discord bot designed to enhance your darts gaming experience by providing real-time statistics, player comparisons, and more.

## Features

- **Real-Time Player Statistics:** Fetch comprehensive stats for your favorite darts players directly within Discord.
- **Player Comparisons:** Compare two players side-by-side to analyze their performance metrics.
- **Last Matches Overview:** Get detailed information about the latest matches, including opponents, dates, and scores.
- **Premium User Support:** Exclusive features and statistics for premium members.
- **Interactive Commands:** Easy-to-use commands to retrieve the information you need quickly.

## Installation

To get started with Dartlog, follow these simple steps:

1. **Clone the Repository:**
    ```bash
    git clone https://github.com/yourusername/dartlog.git
    cd dartlog
    ```

2. **Install Dependencies:**
    Ensure you have Python 3.8 or higher installed. Then, install the required packages:
    ```bash
    pip install -r requirements.txt
    ```

3. **Set Up Environment Variables:**
    Create a `.env` file in the project root and add your Discord bot token:
    ```env
    DISCORD_TOKEN=your_discord_bot_token
    ```

4. **Run the Bot Locally:**
    ```bash
    python run.py
    ```

5. **Deploy to Railway:**
    - Connect your GitHub repository to Railway.
    - Add the [DISCORD_TOKEN](http://_vscodecontentref_/0) environment variable in Railway's project settings.
    - Ensure your [Procfile](http://_vscodecontentref_/1) contains:
      ```plaintext
      worker: python run.py
      ```
    - Deploy the project and monitor the logs for any issues.

## Usage

Once the bot is up and running, you can use the following commands in your Discord server:

- **!stats [player_name] [date_from] [date_to]**
    - Retrieves statistics for the specified player within the given date range.
    - Example:
      ```
      !stats "John Doe" 2023-01-01 2023-03-01
      ```

- **!compare [player1_name] [player2_name]**
    - Compares statistics between two players.
    - Example:
      ```
      !compare "John Doe" "Jane Smith"
      ```

- **!tournament [tournament_name]**
    - Fetches detailed information and statistics about a specific tournament.
    - **Advanced Usage:** You can also specify two players to get insights into their head-to-head performance within the tournament.
    - Examples:
      ```
      !tournament "World Darts Championship"
      !tournament "World Darts Championship" "John Doe" "Jane Smith"
      ```

- **!premiumstats [player_name]**
    - Access premium-level statistics for the specified player, available exclusively to premium users.
    - Example:
      ```
      !premiumstats "John Doe"
      ```

## Contributing

We welcome contributions from the community! To contribute:

1. **Fork the Repository**
2. **Create a New Branch:**
    ```bash
    git checkout -b feature/YourFeature
    ```
3. **Commit Your Changes**
4. **Push to the Branch:**
    ```bash
    git push origin feature/YourFeature
    ```
5. **Open a Pull Request**

Please ensure that all tests pass and adhere to the project's coding standards.

## License

This project is licensed under the MIT License.

---

Thank you for using Dartlog! If you encounter any issues or have suggestions, feel free to reach out or contribute to the repository.
