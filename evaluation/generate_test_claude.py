import httpx
import os
from typing import Dict, Any
from dotenv import load_dotenv
import anthropic

# Load environment variables
load_dotenv()

# Initialize Anthropic client
client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

def generate_candidate_evaluation(job_description: str) -> Dict[str, Any]:
    """
    Generate a candidate evaluation test based on the provided job description.
    """
    try:
        # Construct the prompt
        prompt = f"""We are a technology consulting shop run by software engineers.
        We focus on selectivity of top talent in software engineering disciplines. 
        I would like you to design a custom coding problems take home test
        for the following job description provided.
        For each question, the candidate will provide answers in a code-editor and the answers should be compilable or runnable.
        The test should be able to be completed in 30 minutes.
        
        Job Description:
        {job_description}
        
        Please create a coding problems take home test that includes:
        1. Data Structures and Algorithms
        2. Problem-solving scenarios
        3. System design questions
        4. Code refactoring exercises
        5. Performance optimization challenges
        
        Make sure the questions are:
        - Specific to the role requirements
        - Require deep understanding rather than memorization
        - Include real-world scenarios
        - Test both theoretical knowledge and practical skills
        - Are not easily searchable or AI-answerable
        
        Respond in the following HTML format string with appropriate formatting and sections for instructions, questions and answers
        """
        
        # Call Claude API
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=2000,
            temperature=0.7,
            system="You are an expert software engineering team lead creating software engineering evaluation coding tests questions and answers. Always respond in valid HTML format.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract the generated evaluation
        evaluation = response.content[0].text
        
        return {
            "status": "success",
            "evaluation": evaluation
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def generate_candidate_match(job_description: str, candidate_cv: str) -> Dict[str, Any]:
    """
    Generate a candidate match evaluation based on the job description and candidate's CV.
    Returns a detailed analysis with match score and recommendation.
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
        
        # Call Claude API
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=2000,
            temperature=0.7,
            system="You are an expert technical recruiter with deep experience in evaluating software engineering talent. Always respond in valid HTML format with data attributes for parsing key metrics.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract the generated evaluation
        evaluation = response.content[0].text
        
        return {
            "status": "success",
            "evaluation": evaluation
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def generate_score(candidate_evaluation: str, test_answers: str) -> Dict[str, Any]:
    """
    Generate a score evaluation based on the candidate's test answers.
    Returns a detailed analysis with overall score and answer-specific feedback.
    """
    try:
        # Construct the prompt
        prompt = f"""We are Rayze - a boutique technology company focused on finding the highest caliber technical talent for our clients. 
        Our secret weapon is our screening and interview questions and answers. 
        Please review the candidate technical screen questions and answers provided.

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
        
        # Call Claude API
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=2000,
            temperature=0.7,
            system="You are an expert technical interviewer with deep experience in evaluating software engineering candidates. Always respond in valid HTML format with data attributes for parsing key metrics.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract the generated evaluation
        evaluation = response.content[0].text
        
        return {
            "status": "success",
            "evaluation": evaluation
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# if __name__ == "__main__":
#     # Example usage
#     job_desc = "Senior Software Engineer specializing in React and TypeScript, with experience in building scalable web applications."
#     result = generate_candidate_evaluation(job_desc)
#     if result["status"] == "success":
#         print(result["evaluation"])
#     else:
#         print(f"Error: {result['message']}")