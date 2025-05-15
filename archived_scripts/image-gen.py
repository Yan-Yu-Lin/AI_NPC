import base64
from openai import OpenAI
import os

client = OpenAI()

def generate_image(prompt_text: str, output_filename: str):
    """Generates an image based on the prompt and saves it."""
    try:
        img = client.images.generate(
            model="gpt-image-1", # Reverted to your original model name
            prompt=prompt_text,
            n=1,
            quality="medium",
            size="1024x1024",
            # background="transparent",
        )
        image_bytes = base64.b64decode(img.data[0].b64_json)
        with open(output_filename, "wb") as f:
            f.write(image_bytes)
        print(f"Image saved as {output_filename}")
    except Exception as e:
        print(f"An error occurred: {e}")

def main():
    """Main function to run the CLI tool."""
    print("Welcome to the Image Generator CLI!")
    print("Type your image prompt, or 'quit'/'exit' to stop.")
    
    output_dir = "generated_images"
    os.makedirs(output_dir, exist_ok=True)

    # Determine the starting counter
    counter = 1
    try:
        existing_files = [f for f in os.listdir(output_dir) if f.startswith("output_") and f.endswith(".png")]
        if existing_files:
            max_num = 0
            for f_name in existing_files:
                try:
                    # Extract number: output_NUMBER.png
                    num_str = f_name[len("output_"):-len(".png")]
                    num = int(num_str)
                    if num > max_num:
                        max_num = num
                except ValueError:
                    # In case of non-integer name part, or unexpected format
                    continue 
            counter = max_num + 1
    except OSError:
        # Handle cases where listing directory might fail, though unlikely with makedirs
        print(f"Warning: Could not read directory {output_dir} to determine next file number. Starting from 1.")
        pass

    while True:
        user_prompt = input("Enter what you want to draw: ").strip()
        
        if user_prompt.lower() in ["quit", "exit"]:
            print("Exiting Image Generator. Goodbye!")
            break
            
        if not user_prompt:
            print("Prompt cannot be empty. Please try again.")
            continue

        output_filename = os.path.join(output_dir, f"output_{counter}.png")
        print(f"Generating image for: '{user_prompt}'...")
        generate_image(user_prompt, output_filename)
        counter += 1

if __name__ == "__main__":
    main() 
