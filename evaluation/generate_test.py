import httpx
from openai import OpenAI
import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# # Initialize OpenAI client
# client = OpenAI(
#     api_key=os.getenv("OPEN_AI_KEY")
# )
class CustomHTTPClient(httpx.Client):
        def __init__(self, *args, **kwargs):
            kwargs.pop("proxies", None)  # Remove the 'proxies' argument if present
            super().__init__(*args, **kwargs)

client = OpenAI(http_client=CustomHTTPClient())


def generate_candidate_evaluation(job_description: str) -> Dict[str, Any]:
    """
    Generate a candidate evaluation test based on the provided job description.
    """
    print('job_description is ', job_description);
    print('am here')
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
        
        # Call OpenAI API with the new format
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert software engineering team lead creating software engineering evaluation coding tests questions and answers. Always respond in valid HTML format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        # Extract the generated evaluation (updated for v1.12.0)
        evaluation = response.choices[0].message.content
        # evaluation = response.choices[0].message.content.replace('```json', '').replace('```', '').strip()

        #print(evaluation)
        
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
        #print(prompt);
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert technical recruiter with deep experience in evaluating software engineering talent. Always respond in valid HTML format with data attributes for parsing key metrics."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        # Extract the generated evaluation
        evaluation = response.choices[0].message.content
        
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
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert technical interviewer with deep experience in evaluating software engineering candidates. Always respond in valid HTML format with data attributes for parsing key metrics."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        # Extract the generated evaluation
        evaluation = response.choices[0].message.content
        
        return {
            "status": "success",
            "evaluation": evaluation
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def generate_candidate_cv(candidate_cv: str) -> Dict[str, Any]:
    """
    Generate a structured JSON object from a candidate's CV containing key information.
    
    Args:
        candidate_cv (str): The candidate's CV/resume text
        
    Returns:
        Dict[str, Any]: JSON object containing parsed candidate information
    """
    try:
        prompt = f"""Please analyze the following CV and extract key information into a structured JSON format.
        
        CV Content:
        {candidate_cv}
        
        Extract and return ONLY a JSON object with the following fields:
        - name: candidate's full name
        - phone: phone number (if available)
        - email: email address (if available)
        - role: most current role
        - location: city or country
        - linkedin: LinkedIn URL (if available)
        - key_skills: array of main technical and professional skills
        - key_achievements: array of notable professional accomplishments
        - strengths: array of candidate's core strengths
        - gaps: array of potential skill or experience gaps
        - cv_summary: summary of the candidate cv including the key_skills, key_achievements, gaps
        
        Ensure the response is a valid JSON object with these exact field names.
        """
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert at parsing resumes and extracting structured information. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        # Extract the generated JSON
        parsed_cv = response.choices[0].message.content
        
        return {
            "status": "success",
            "candidate_info": parsed_cv
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def generate_job_desc(job_desc: str) -> Dict[str, Any]:
    """
    Generate a structured JSON object from a job description containing key information.
    
    Args:
        job_desc (str): The clients job descroption
        
    Returns:
        Dict[str, Any]: JSON object containing parsed job description
    """
    print(job_desc)
    try:
        prompt = f"""Please analyze the following job description and extract key information into a structured JSON format.
        
        Job Description Content:
        {job_desc}
        
        Extract and return ONLY a JSON object with the following fields:
        - role_name: The Open Role name
        - background: background information on the team, company, project if available
        - role_desc: any role description on what the candidate will perform if available
        - responsibilites: array of all the responsibilities of this role
        - candidate_requirements: array of candidate requirements and skills required and technical competencies
        - must_have: array of must have skills and technical competencises
        - nice_to_have: array of nice to have skills and technical competencies
        - technical_skills: array of technical skills and competencies
        
        Ensure the response is a valid JSON object with these exact field names.
        """
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert at parsing job descriptions and extracting structured information. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        # Extract the generated JSON
        parsed_jd = response.choices[0].message.content
        
        return {
            "status": "success",
            "job_desc": parsed_jd
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