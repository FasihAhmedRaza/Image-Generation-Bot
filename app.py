import os
import base64
from flask import Flask, render_template, request, jsonify
import openai
from dotenv import load_dotenv
import json



from flask_cors import CORS  # Add this at the top with other imports
app = Flask(__name__)
CORS(app)  # Add this right after creating your Flask app

app.config["UPLOAD_FOLDER"] = "static/uploads"

# Load environment variables from .env file
load_dotenv()

# Get the API key from the environment variable
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")

client = openai.OpenAI(api_key=api_key)

# Function to encode image to base64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


# Global conversation history with a welcome message
conversation_history = [{"user": "", "ai": "Welcome to Ice Butcher! How can I assist you today? you can gernate ice sckupers form that feel free to make 🧊"}]


@app.route("/", methods=["GET"])
def index():
    # Render the template and pass the initial conversation history
    return render_template("index.html", conversation_history=conversation_history)




conversation_history = []
@app.route("/chatbot", methods=["POST"])
def chatbot():
    
    # Define a list of keywords that should trigger DALL·E image generation
    image_generation_keywords = ["generate", "create", "make", "design", "draw", "build", "craft" , "imagine",  "sketch", "construct","sculpt" ]

    user_input = request.form.get("user_input", "").strip().lower()
    uploaded_file = request.files.get("image")

    try:

        # Create the custom prompt with matched results
        custom_prompt = f"""
        You are an AI assistant for an ice sculpture company named "Ice Butcher", you can only create images from users prompts and input images.


        Message to show along with the images response:
        this is the Rendering of what we have done for other clients, we can also customize it to your event theme and logo, So! you want like this? (change your tone accordingly)

         - Users can only create ice sculptures in this chatbot if their message starts with one of the following words: 
        "generate", "create", "make", "design", "draw", "build", "craft", "imagine", "sketch", "construct", "sculpt".
        """
        conversation_text = "\n".join([f"User: {entry['user']}\nAI: {entry['ai']}" for entry in conversation_history])
        full_prompt = f"{custom_prompt}\n{conversation_text}\nUser: {user_input}\nAI:"


        # If there's an uploaded file (image)';mn
        if uploaded_file:
            image_path = "uploaded_image.jpg"
            uploaded_file.save(image_path)
            
            instruction_text = """
            Describe the geometrical features of this image for an ice Sculpture.
            The ice should have a natural texture with light refraction.
            """

            base64_image = encode_image(image_path)
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": instruction_text},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }]
            )

            gpt_response = completion.choices[0].message.content

            dalle_prompt = f"""
            Create an image of an ice Sculpture.
            The Sculpture should be a carving on a thick ice block.
            The ice should have a natural texture with light refraction.
            {gpt_response}
            
            The ice Sculpture should appear carved from genuine translucent ice, with a natural, slightly imperfect finish.
            Place the Sculpture on a wooden table with a black background for contrast.
            Avoid intricate patterns, sharp edges, or overly fine details, it should be very basic as possible.
            Focus on natural ice textures, slight frost buildup, and subtle light refraction.
            The image should resemble a high-quality photograph taken with a professional DSLR camera, capturing the essence of an authentic, handcrafted ice Sculpture.
            The final image will only include the ice sculpture .
            
            IMPORTANT: 
            - Only provide realistic designs that are possible to make with real ice.
            - Avoid any tiny or overly intricate designs that are not feasible for actual ice carving.
            
            """

        
        # If the user input contains "generate", pass the prompt to DALL·E
        elif any(user_input.startswith(keyword) for keyword in image_generation_keywords):
            dalle_prompt = f"""
            Create images of ice Sculpture.
            Every image should emphasize natural ice .
            Avoid adding too much details, keep it as simple as possible.
            
            {user_input}
            IMPORTANT: - The Ice Sculpture primarily focuses on detailed Sculpture.
            Only provide realistic designs that are possible to make with real ice.
            The ice Sculpture should appear carved from genuine translucent ice, with a natural, slightly imperfect finish.
            Place the Sculpture on a wooden table with a black background for contrast.
            Avoid intricate patterns, sharp edges, or overly fine details, it should be very basic as possible.
            Focus on natural ice textures, slight frost buildup, and subtle light refraction.
            The image should resemble a high-quality photograph taken with a professional DSLR camera, capturing the essence of an authentic, handcrafted ice Sculpture.
            The final image will only include the ice engraved sculpture , no human should be present in the image.
            Do not include any tiny or overly intricate designs that are not feasible with real ice.

      
            """
        
        # Handle other chatbot input
        else:
            prompt_with_custom = f"{full_prompt}\n{user_input}"
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt_with_custom}]
            )
            gpt_response = completion.choices[0].message.content
            conversation_history.append({"user": user_input, "ai": gpt_response})
            return jsonify({"response": gpt_response})
        


        # Generate image with DALL-E 3
        response = client.images.generate(
            model="dall-e-3",
            prompt=dalle_prompt,
            size="1024x1024",
            quality="hd",
            n=1,
        )

        generated_image_url = response.data[0].url
        return jsonify({"response": "Here is your ice Sculpture:\n", "image_url": generated_image_url})

    except Exception as e:
        return jsonify({"response": f"Error: {str(e)}"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
