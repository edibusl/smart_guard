# Smart Guard
## Smart home security camera
A raspberry pi camera that detects motion and sends reports securely to the cloud.
<br>
On the backend side a set of rules is applied to detect and recognize faces in order to decide whether to upload frames of suspicious activity.
<br>
## Costs
To reduce costs all backend processing anc communication is done through AWS Lambda functions and IoT Core.
<br>
 
## Face detection and recognition model
Using the model and code from: https://www.pyimagesearch.com/2018/09/24/opencv-face-recognition/
<br>
<br>
The model workflow:
### Extract embeddings
Detect faces and extract face embeddings from a dataset of image files with faces.
<br>
Use OpenCV face detector model and extract embeddings torch model.  

Input:
1. Dataset of images and their labels (determined by the directory name)
2. Detector - OpenCV face detection model (Caddemodel file - res10_300x300_ssd_iter_140000.caffemodel) - An OpenCV model to detect faces
3. Embedding Model - Face embedding model (openface_nn4.small2.v1.t7). A model in a torch file for extracting embeddings from the detected face.

Output:
1. embeddings.pickle - A pickle file with embeddings of all face detections of the dataset including their labels

### Train model
Use sklearn LabelEncoder and SVM support vector machine to train a model to recognize faces in an image.

Input:

1. embeddings.pickle (from previous step)

Output:

1. Recognizer - A pickle file with the trained model to recognize faces
2. Label Encoder - A pickle file with the label encoder mapping 


### Recognize image
Detect faces in an image, extract embeddings, recognize the faces and label them

Input:

1. Image - The image to recognize
1. Detector - From previous steps
1. Embedding Model - From previous steps
1. Recognizer - From previous steps
1. Label Encoder - From previous steps

Output:
1. Detected faces and their recognized labels