import requests
import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def generate_candidate_evaluation(job_description: str, api_key: str, team_id: str = None) -> Dict[str, Any]:
    """
    Generate a candidate evaluation test based on the provided job description using Grok 3.
    
    Args:
        job_description (str): The job description to base the evaluation on.
        api_key (str): xAI Grok API key.
        team_id (str, optional): Team ID for API access, if required.
    
    Returns:
        Dict[str, Any]: Result containing status and evaluation or error message.
    """
    try:
        # Construct the prompt
        prompt = f"""Based on the following job description, create a relevant and comprehensive candidate take home coding test.
        The test should be challenging but fair, and should not be easily answerable by AI tools. It should be a coding test that is relevant to the job description.
        The test should take 30 minutes to complete at home.

        Job Description:
        {job_description}

        Please create a test that includes:
        1. Data Structures and Algorithms
        2. Problem-solving coding questions
        3. System design questions
        4. Code refactoring challenges
        5. Performance optimization challenges

        Make sure the questions are:
        - Specific & relevant to the role requirements
        - Require deep understanding rather than memorization
        - Include real-world scenarios
        - Test both theoretical knowledge and practical skills
        - Are not easily searchable or AI-answerable
        - Are not easily googleable

        Respond in a well-structured HTML format that includes:
        - Instructions for the candidate and letting them know to please NOT use GPT as we use GPT detectors. Also please write concise human readable clean code
        - Questions with boiler plate code for them to save time
        - Submission with comments in 1 single .txt file. Do not provide instructions on emails or how to submit.
        - Professional formatting and clear section for each question
        """

        # xAI Grok API endpoint
        GROK_API_URL = "https://api.x.ai/v1/chat/completions"

        # Headers for the API request
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        if team_id:
            headers["X-Team-ID"] = team_id  # Include team ID if required

        # Payload for the API request
        payload = {
            "model": "grok-2-1212",  # Use Grok 3 model
            "messages": [
                {"role": "system", "content": "You are a development lead creating a take home exam for candidates. The test will evaluate their coding expertise which will help us determine if they are technically capable and a good fit for the role."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }

        # Make the API call to Grok
        response = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=30)

        # Check if the request was successful
        response.raise_for_status()

        # Parse the response
        response_data = response.json()
        evaluation = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")

        if not evaluation:
            raise ValueError("No evaluation generated from Grok API")

        return {
            "status": "success",
            "evaluation": evaluation
        }

    except requests.exceptions.HTTPError as e:
        if response.status_code == 403:
            return {
                "status": "error",
                "message": "Access denied. Check API key or team ID. Possible 'Access to team denied' error."
            }
        return {
            "status": "error",
            "message": f"HTTP error calling Grok API: {str(e)}"
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Network error calling Grok API: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}"
        }

def generate_candidate_match(job_description: str, candidate_cv: str, api_key: str, team_id: str = None) -> Dict[str, Any]:
    """
    Generate a candidate match evaluation based on the job description and candidate's CV using Grok 3.
    
    Args:
        job_description (str): The job description to match against.
        candidate_cv (str): The candidate's CV text.
        api_key (str): xAI Grok API key.
        team_id (str, optional): Team ID for API access, if required.
    
    Returns:
        Dict[str, Any]: Result containing status and evaluation or error message.
    """
    try:
        # Construct the prompt
        prompt = f"""We are Rayze - a boutique technology company focused on finding the highest caliber technical talent for our clients.

        Please analyze the following job requirements and candidate CV to provide a detailed evaluation:

        Job Description:
        {job_description}

        Candidate CV:
        {candidate_cv}

        Please provide a comprehensive evaluation that includes:
        1. An overall match score (0-100)
        2. A clear recommendation (RECOMMEND or DO NOT RECOMMEND)
        3. Required skills analysis with individual ratings (0-100) for each skill
        4. Strengths and skill gaps analysis
        5. Notable achievements analysis
        6. Average tenure calculation and role progression analysis

        Respond in a well-structured HTML format that includes:
        - A parsable recommendation summary section with data-attributes for score and recommendation
        - Detailed skills assessment
        - Qualitative analysis sections
        - Professional formatting and clear section hierarchy
        """

        # xAI Grok API endpoint
        GROK_API_URL = "https://api.x.ai/v1/chat/completions"

        # Headers for the API request
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        if team_id:
            headers["X-Team-ID"] = team_id

        # Payload for the API request
        payload = {
            "model": "grok-2-1212",
            "messages": [
                {"role": "system", "content": "You are an expert technical recruiter with deep experience in evaluating software engineering talent. Always respond in valid HTML format with data attributes for parsing key metrics."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }

        # Make the API call to Grok
        response = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        # Parse the response
        response_data = response.json()
        evaluation = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")

        if not evaluation:
            raise ValueError("No evaluation generated from Grok API")

        return {
            "status": "success",
            "evaluation": evaluation
        }

    except requests.exceptions.HTTPError as e:
        if response.status_code == 403:
            return {
                "status": "error",
                "message": "Access denied. Check API key or team ID. Possible 'Access to team denied' error."
            }
        return {
            "status": "error",
            "message": f"HTTP error calling Grok API: {str(e)}"
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Network error calling Grok API: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}"
        }

def generate_score(candidate_evaluation: str, test_answers: str, api_key: str, team_id: str = None) -> Dict[str, Any]:
    """
    Generate a score evaluation based on the candidate's test answers using Grok 3.
    
    Args:
        candidate_evaluation (str): The original test questions.
        test_answers (str): The candidate's answers to the test.
        api_key (str): xAI Grok API key.
        team_id (str, optional): Team ID for API access, if required.
    
    Returns:
        Dict[str, Any]: Result containing status and evaluation or error message.
    """
    try:
        # Construct the prompt
        prompt = f"""We are Rayze - a boutique technology company focused on finding the highest caliber technical talent for our clients. 
        Our secret weapon is our screening and interview questions and answers. 
        Please review the candidate technical screen questions in the questions file and corresponding answers provided in the answers file.

        Technical Questions:
        {candidate_evaluation}

        Candidate Answers:
        {test_answers}

        Please provide a comprehensive evaluation that includes:
        1. An overall score (0-100) at the top with data-attribute for parsing
        2. A concise recommendation summary
        3. Individual scores and feedback for each answer
        4. Key strengths and areas for improvement
        5. Technical depth and problem-solving ability assessment

        Respond in a well-structured HTML format that includes:
        - A parsable score section with data-attributes
        - Clear answer-by-answer analysis
        - Professional formatting and clear section hierarchy
        """

        # xAI Grok API endpoint
        GROK_API_URL = "https://api.x.ai/v1/chat/completions"

        # Headers for the API request
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        if team_id:
            headers["X-Team-ID"] = team_id

        # Payload for the API request
        payload = {
            "model": "grok-2-1212",
            "messages": [
                {"role": "system", "content": "You are an expert technical interviewer with deep experience in evaluating software engineering candidates. Always respond in valid HTML format with data attributes for parsing key metrics."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }

        # Make the API call to Grok
        response = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        # Parse the response
        response_data = response.json()
        evaluation = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")

        if not evaluation:
            raise ValueError("No evaluation generated from Grok API")

        return {
            "status": "success",
            "evaluation": evaluation
        }

    except requests.exceptions.HTTPError as e:
        if response.status_code == 403:
            return {
                "status": "error",
                "message": "Access denied. Check API key or team ID. Possible 'Access to team denied' error."
            }
        return {
            "status": "error",
            "message": f"HTTP error calling Grok API: {str(e)}"
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Network error calling Grok API: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}"
        }

# if __name__ == "__main__":
#     # Example usage for testing
#     sample_job_description = "Senior Python Developer with experience in FastAPI, SQLAlchemy, and AWS."
#     grok_api_key = os.getenv("GROK_API_KEY")
#     grok_team_id = os.getenv("GROK_TEAM_ID")  # Optional: Set GROK_TEAM_ID in .env if needed

#     if not grok_api_key:
#         print("Grok API key not found. Please set GROK_API_KEY in environment variables.")
#     else:
#         result = generate_candidate_evaluation(sample_job_description, grok_api_key, grok_team_id)
#         print(result)