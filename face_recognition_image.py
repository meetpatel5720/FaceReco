import pickle

import numpy
from PIL import Image
import PIL
import numpy as np
from imutils import face_utils

import facenet
from constants import *
import cv2
import tensorflow.compat.v1 as tf

tf.disable_v2_behavior()

image_size = 182
input_image_size = 160

with tf.Graph().as_default():
    gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.6)
    sess = tf.Session(config=tf.ConfigProto(gpu_options=gpu_options, log_device_placement=False))
    with sess.as_default():
        HumanNames = os.listdir(CROPPED_IMAGE_DIR)
        HumanNames.sort()
        print(HumanNames)

        print('Loading Model...')
        facenet.load_model(MODEL_PATH)
        images_placeholder = tf.get_default_graph().get_tensor_by_name("input:0")
        embeddings = tf.get_default_graph().get_tensor_by_name("embeddings:0")
        phase_train_placeholder = tf.get_default_graph().get_tensor_by_name("phase_train:0")
        embedding_size = embeddings.get_shape()[1]

        classifier_filename_exp = os.path.expanduser(CLASSIFIER_PATH)
        with open(classifier_filename_exp, 'rb') as infile:
            (model, class_names) = pickle.load(infile, encoding='latin1')

        # img = cv2.imread(os.path.join(TEST_IMAGE_DIR, "IMG_20200227_1514481.jpg"))
        # img = cv2.resize(img, (int(img.shape[1] / 5), int(img.shape[0] / 5)))
        pil_img = Image.open(os.path.join(TEST_IMAGE_DIR, "IMG_0049.jpg"))
        # pil_img = pil_img.resize((int(pil_img.size[0] / 5), int(pil_img.size[1] / 5)), PIL.Image.ANTIALIAS)
        img = cv2.cvtColor(numpy.array(pil_img), cv2.COLOR_RGB2BGR)


def recognize_faces(image):
    find_results = []

    if image.ndim == 2:
        frame = facenet.to_rgb(image)
    frame = image[:, :, 0:3]
    faces = detector(frame, 1)
    nrof_faces = len(faces)

    print('Detected_FaceNum: %d' % nrof_faces)

    if nrof_faces > 0:

        cropped = []
        scaled = []
        scaled_reshape = []
        bb = np.zeros((nrof_faces, 4), dtype=np.int32)

        for i, face in enumerate(faces):
            emb_array = np.zeros((1, embedding_size))
            (x, y, w, h) = face_utils.rect_to_bb(face)
            bb[i][0] = x
            bb[i][1] = y
            bb[i][2] = x + w
            bb[i][3] = y + h

            # inner exception
            if bb[i][0] <= 0 or bb[i][1] <= 0 or bb[i][2] >= len(frame[0]) or bb[i][3] >= len(frame):
                print('Face is very close!')
                continue

            cropped.append(frame[bb[i][1]:bb[i][3], bb[i][0]:bb[i][2], :])
            cropped[i] = facenet.flip(cropped[i], False)
            scaled.append(cv2.resize(cropped[i], (image_size, image_size), interpolation=cv2.INTER_LINEAR))
            scaled[i] = cv2.resize(scaled[i], (input_image_size, input_image_size),
                                   interpolation=cv2.INTER_LINEAR)
            scaled[i] = facenet.prewhiten(scaled[i])
            scaled_reshape.append(scaled[i].reshape(-1, input_image_size, input_image_size, 3))
            feed_dict = {images_placeholder: scaled_reshape[i], phase_train_placeholder: False}
            emb_array[0, :] = sess.run(embeddings, feed_dict=feed_dict)
            predictions = model.predict_proba(emb_array)
            # print(predictions)
            best_class_indices = np.argmax(predictions, axis=1)
            best_class_probabilities = predictions[np.arange(len(best_class_indices)), best_class_indices]
            # print("predictions")
            print(best_class_indices, ' with accuracy ', best_class_probabilities)

            # print(best_class_probabilities)
            if best_class_probabilities > 0.20:
                cv2.rectangle(frame, (bb[i][0], bb[i][1]), (bb[i][2], bb[i][3]), (0, 255, 0),
                              6)  # boxing face

                # plot result idx under box
                text_x = bb[i][0]
                text_y = bb[i][3] + 20
                # print('Result Indices: ', best_class_indices[0])
                # print(HumanNames)
                for H_i in HumanNames:
                    if HumanNames[best_class_indices[0]] == H_i:
                        result_names = HumanNames[best_class_indices[0]]
                        cv2.putText(frame, result_names, (text_x, text_y), cv2.FONT_HERSHEY_COMPLEX_SMALL,
                                    5, (0, 0, 255), thickness=5, lineType=2)
    else:
        print('Alignment Failure')
    frame = cv2.resize(frame, (int(frame.shape[1] / 5), int(frame.shape[0] / 5)))
    return frame


new_img = recognize_faces(img)
cv2.imshow("Camera", new_img)
cv2.waitKey(0)
cv2.destroyAllWindows()
