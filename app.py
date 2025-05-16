import os
import base64
from flask import Flask, render_template, request, jsonify
import openai
from dotenv import load_dotenv
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

app.config["UPLOAD_FOLDER"] = "static/uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")

client = openai.OpenAI(api_key=api_key)

# Sculpture state management
current_sculpture = {
    "name": "",
    "description": "",
    "elements": {
        "tip": "",
        "upper_body": "",
        "middle_body": "",
        "lower_body": "",
        "base": "",
        "decorations": []
    },
    "textures": ["clear", "frosty"],
    "modifications": []
}

conversation_history = [
    {
        "user": "",
        "ai": (
            "Welcome to **Ice Sculptures Rendering**! I'm your visual artist assistant, "
            "specializing in designing and modifying realistic ice sculptures. 🧊\n\n"
            "- You can describe a sculpture you'd like me to create\n"
            "- Or upload an image you'd like me to turn into an ice sculpture\n\n"
            "I'll remember details across our conversation and stay completely in the ice art context!"
        )
    }
]

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", conversation_history=conversation_history)

@app.route("/chatbot", methods=["POST"])
def chatbot():
    global current_sculpture, conversation_history

    user_input = request.form.get("user_input", "").strip()
    uploaded_file = request.files.get("image")

    try:
        if uploaded_file:
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], "uploaded_image.jpg")
            uploaded_file.save(image_path)
            base64_image = encode_image(image_path)

            image_analysis = client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "You are an expert ice sculptor.\n"
                                "Analyze this image to help convert it into a realistic ice sculpture. "
                                "Identify:\n"
                                "1. Main sculpture-worthy components\n"
                                "2. Best parts for ice carving\n"
                                "3. Modifications or engravings that would enhance it\n"
                                "4. Ice-specific considerations for weight, balance, fragility"
                            )
                        },
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }]
            ).choices[0].message.content

            conversation_history.append({
                "user": "[Uploaded image]",
                "ai": image_analysis
            })

            return jsonify({"response": image_analysis})

        # Create system prompt
        system_prompt = f"""
        You are Ice Sculptures Rendering — a visual artist assistant who specializes in generating and modifying
        photo-realistic ice sculptures. Stay 100% in-character and always follow these instructions:

        1. All sculptures must look like they’re made of ice — clear, frosty, or textured.
        2. Respect the current sculpture's memory. Never forget previous changes or details.
        3. Follow modifications like adding names, symbols, or crowns precisely.
        4. Only describe components like: tip, upper body, middle body, lower body, base, decorations.
        5. Confirm and summarize user changes before finalizing the sculpture.
        6. Never suggest impossible ice structures — realism is key.
        7. Respond in a friendly, helpful artist tone and never break ice-themed character.

        Current Sculpture State:
        - Name: {current_sculpture['name']}
        - Description: {current_sculpture['description']}
        - Elements: {current_sculpture['elements']}
        - Textures: {', '.join(current_sculpture['textures'])}
        - Modifications: {current_sculpture['modifications']}
        """

        # Get GPT-4o response
        text_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
        ).choices[0].message.content

        conversation_history.append({"user": user_input, "ai": text_response})

        # Generate ice sculpture image using DALL·E 3
        dalle_prompt = f"""
        Create a photorealistic image of an ice sculpture based on the following:

        - Theme or Name: {current_sculpture['name'] or 'Abstract Ice Sculpture'}
        - Description: {current_sculpture['description'] or user_input}
        - Style: Expert-level ice carving
        - Materials: Made entirely of clear and frosty ice
        - Texture: Realistic ice surface and reflections
        - Lighting: Studio lighting to enhance refraction
        - Background: Plain or softly lit to emphasize the sculpture
        - Components: Tip, upper body, middle body, lower body, base, and any decorations

        Notes:
        - The sculpture must appear physically possible to carve from real ice.
        - Avoid cartoonish or impossible forms.
        """

        image_response = client.images.generate(
            model="dall-e-3",
            prompt=dalle_prompt,
            size="1024x1024",
            quality="hd",
            n=1,
        )

        return jsonify({
            "response": text_response,
            "image_url": image_response.data[0].url,
            "sculpture_state": current_sculpture
        })

    except Exception as e:
        return jsonify({"response": f"Error: {str(e)}"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
