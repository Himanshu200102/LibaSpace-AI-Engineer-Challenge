"""Main entry point for Lever job application agent."""
import asyncio
import json
import logging
import sys
from pathlib import Path
from core.agent import LeverJobApplicant

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point."""
    job_url = "https://jobs.lever.co/ekimetrics/d9d64766-3d42-4ba9-94d4-f74cdaf20065"
    
    if len(sys.argv) > 1:
        job_url = sys.argv[1]
    
    # Load resume data
    resume_path = Path(__file__).parent / "data" / "resume.json"
    with open(resume_path, "r") as f:
        resume_data = json.load(f)
    
    # Resume file path
    resume_file = Path(__file__).parent / "data" / "resume.pdf"
    resume_file_path = str(resume_file) if resume_file.exists() else None
    
    if not resume_file_path:
        logger.warning("No resume.pdf found in data/ folder")
    
    # Apply
    applicant = LeverJobApplicant(resume_data, resume_file_path)
    result = await applicant.apply(job_url)
    
    # Print results
    print("\n" + "=" * 60)
    print("APPLICATION RESULT")
    print("=" * 60)
    print(f"Success: {result['success']}")
    
    print(f"\nFields Filled ({len(result['fields_filled'])}):")
    for field in result['fields_filled']:
        print(f"  ✓ {field}")
    
    if result.get('fields_empty'):
        print(f"\nFields Still Empty ({len(result['fields_empty'])}):")
        for field in result['fields_empty']:
            print(f"  ⚠ {field}")
    
    if result['errors']:
        print(f"\nErrors ({len(result['errors'])}):")
        for error in result['errors']:
            print(f"  ✗ {error}")
    
    # Summary
    print("\n" + "-" * 60)
    filled = len(result['fields_filled'])
    empty = len(result.get('fields_empty', []))
    errors = len(result['errors'])
    print(f"SUMMARY: {filled} filled, {empty} empty, {errors} errors")
    print("=" * 60 + "\n")
    
    # Save result
    with open("lever_result.json", "w") as f:
        json.dump(result, f, indent=2)
    print("Result saved to lever_result.json")


if __name__ == "__main__":
    asyncio.run(main())

