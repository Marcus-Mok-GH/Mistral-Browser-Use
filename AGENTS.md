<general_rules>
- Before creating new functions, check the existing files (`browser_automation.py`, `element_detector.py`, `mistral_client.py`, `utils.py`) to see if similar functionality already exists.
- Utilize the helper functions in `utils.py` for common tasks like file operations, timestamp generation, and image encoding.
- All major business logic is contained within the `app.py` file, which serves as the entry point for the Streamlit application. When adding new features, consider if they should be part of the core application logic or abstracted into one of the utility modules.
</general_rules>
<repository_structure>
The repository is structured as a Streamlit application with a clear separation of concerns:
- `app.py`: The main application file that handles the user interface and orchestrates the automation process.
- `browser_automation.py`: Contains the `BrowserAutomation` class, which manages all Selenium-related browser interactions, such as starting the browser, navigating, and interacting with web elements.
- `element_detector.py`: Includes the `ElementDetector` class, responsible for processing screenshots, identifying interactive elements, and annotating them.
- `mistral_client.py`: Houses the `MistralClient` class for communicating with the Mistral AI API to analyze screenshots and decide on the next action.
- `utils.py`: A collection of utility functions for various tasks, including file and directory management, image encoding, and data serialization.
- `requirements.txt`: Specifies the Python dependencies for the project.
- `packages.txt`: Defines system-level dependencies required for cloud-based deployments, such as on Streamlit Cloud.
</repository_structure>
<dependencies_and_installation>
- All Python dependencies are listed in the `requirements.txt` file and can be installed using `pip install -r requirements.txt`. It is recommended to use a virtual environment.
- The application requires Firefox to be installed. For local development, ensure Firefox is installed on your system. For cloud deployments, `firefox-esr` is installed via the `packages.txt` file.
- The `geckodriver` for Firefox automation is automatically downloaded and managed by the `webdriver-manager` library, so no manual installation is typically required.
</dependencies_and_installation>
<testing_instructions>
- While there is no formal testing suite, the project includes examples of simple tests. For instance, the `mistral_client.py` file has a `test_connection` method to verify the API connection.
- When adding new functionality, especially to the client or automation modules, it is recommended to include a similar test method to ensure the new code works as expected.
- To run a test, you can add a simple script or a `if __name__ == "__main__":` block to the relevant file to execute the test method.
</testing_instructions>
<pull_request_formatting>
</pull_request_formatting>
