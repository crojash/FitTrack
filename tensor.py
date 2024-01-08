import tflite_runtime.interpreter as tflite
import numpy as np
from PIL import Image

# Load the TFLite model and allocate tensors.
interpreter = tflite.Interpreter(model_path="model_path")
interpreter.allocate_tensors()

# Get input and output tensors.
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# Load the image and preprocess it
image = Image.open("dumbells.jpg").resize((224, 224)).convert('RGB')  # Convert image to RGB
image = np.array(image, dtype=np.uint8)  # Convert image to numpy array with uint8 type
image = np.expand_dims(image, axis=0)  # Add batch dimension

# Point the data to be used for testing and run the interpreter
interpreter.set_tensor(input_details[0]['index'], image)
interpreter.invoke()

# Obtain results and map them to the classes
predictions = interpreter.get_tensor(output_details[0]['index'])
predicted_class = np.argmax(predictions)  # Get the class with highest probability

# Load the labels
with open('labels_mobilenet_quant_v1_224.txt', 'r') as f:
    labels = [line.strip() for line in f.readlines()]

# Print the result
print(f'Predicted Class: {labels[predicted_class]}, Probability: {predictions[0][predicted_class]}')