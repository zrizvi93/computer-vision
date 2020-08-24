import cv2
import face_recognition
import numpy as np
import os
import re
import getpass
from subprocess import Popen, PIPE

USER = getpass.getuser()

# check for known/ directory
PROJECT_PATH = os.path.abspath(os.path.dirname(__file__))
# PROJECT_PATH = os.path.abspath(os.getcwd())
KNOWN_PATH = os.path.join(PROJECT_PATH, 'known/')
WHITELIST_PATH = os.path.join(KNOWN_PATH, 'whitelist/')
BLACKLIST_PATH = os.path.join(KNOWN_PATH, 'blacklist/')
CHECK_FOLDER = os.path.isdir(KNOWN_PATH)


def CaptureFace(name,access):
    destination_folder = WHITELIST_PATH if access == True else BLACKLIST_PATH
    cam = cv2.VideoCapture(0)
    cv2.namedWindow("Capturing Face ID")
    img_counter = 0
    while True:
        ret, frame = cam.read()
        if not ret:
            print("failed to grab frame")
            break
        cv2.imshow("Capturing Face ID", frame)

        k = cv2.waitKey(1)
        if k % 256 == 27:
            # ESC pressed
            print("Escape hit, closing...")
            break
        elif k % 256 == 32:
            # SPACE pressed
            img_name = "{}_{}".format(name, img_counter)
            cv2.imwrite(destination_folder + img_name + '.jpg', frame)
            print("saved {}{}.jpg".format(destination_folder, img_name))
            img_counter += 1
    cam.release()
    cv2.destroyAllWindows()


def Setup():
    while True:
         query = input("Welcome to the initial set-up for your MacOS Sentry!\n"
                       "Well-lit surroundings are advised for this portion.\n"
                       "Please confirm Y/N to continue:\n")
         Fl = query.strip().lower()[0]
         if query == '' or not Fl in ['y','n']:
            print("Sorry... I didnt quite get that. Please answer with yes or no. :)\n")
         else:
            break
    if Fl == 'n':
        print("No worries! We can set up another time.")
    if Fl == 'y':
        print("Great! Let's get started.\n"
              "Please verify your password to authorize macOS-sentry.")
        # temporarily disable bash history
        os.system("unset HISTFILE")
        # add keychain pass
        add = "security -q add-generic-password -a {} -s macOS-sentry -p $(security -q find-generic-password -a {} -w)".format(USER,USER)
        os.system(add)
        print("Authorized! Now collecting administrator face identity.")
        print("Press SPACE to capture face photo. To retake, press SPACE again. To continue, press ESC.")
        os.makedirs(KNOWN_PATH)
        os.makedirs(os.path.join(KNOWN_PATH, 'whitelist/'))
        os.makedirs(os.path.join(KNOWN_PATH, 'blacklist/'))
        print("created directory : ", KNOWN_PATH)
        CaptureFace("admin",True)


def LockScreen():
    cmd = """osascript -e 'tell application "system events" to key code 12 using {command down, control down}'"""
    os.system(cmd)


# def UnlockScreen():
#     cmd = """osascript<<END
#     tell application "System Events"
# 		if ((get name of every process) contains "ScreenSaverEngine") then
# 			set pw to (do shell script "security find-generic-password -a {} -w")
# 			tell application "ScreenSaverEngine" to quit
# 			delay 0.5
# 			keystroke return
# 			keystroke pw
# 			keystroke return
# 			-- set require password to wake of security preferences to false
# 		end if
# 	end tell
#     END""".format(USER)
#     os.system(cmd)
#     # p = Popen(UnlockScreen(), shell=True)
#     # p.terminate()
#     # return p

def Sentry():
    p = re.compile("(.*)_\d+\.jpg")
    known_id_paths = []
    known_id_names = []
    known_id_access = []

    for root, dirs, files in os.walk(KNOWN_PATH):
        for x in files:
            if p.match(x):
                known_id_paths.append(os.path.join(root,x))
                known_id_names.append(p.match(x).group(1))
                known_id_access.append(os.path.basename(root))

    known_face_encodings = []
    known_face_names = []

    for i in range(len(known_id_paths)):
        globals()['image_{}'.format(i)] = face_recognition.load_image_file(known_id_paths[i])
        globals()['image_encoding_{}'.format(i)] = face_recognition.face_encodings(globals()['image_{}'.format(i)])[0]
        known_face_encodings.append(globals()['image_encoding_{}'.format(i)])
        known_face_names.append(known_id_names[i])

    # Initialize some variables
    face_locations = []
    face_encodings = []
    face_names = []
    process_this_frame = True

    prev_frame_face_names = []

    while True:
        # Get a reference to webcam #0 (the default one)
        video_capture = cv2.VideoCapture(0)

        curr_ret, current_frame = video_capture.read()

        if curr_ret and process_this_frame:
            # Resize frame of video to 1/4 size for faster face recognition processing
            small_frame = cv2.resize(current_frame, (0, 0), fx=0.25, fy=0.25)

            # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
            rgb_small_frame = small_frame[:, :, ::-1]

            # Find all the faces and face encodings in the current frame of video
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

            face_names = []

            for face_encoding in face_encodings:
                # See if the face is a match for the known face(s)
                matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                name = "Unknown"

                # If a match was found, use the known face with the smallest distance to the new face
                face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = known_face_names[best_match_index]

                face_names.append(name)

            conditions = ['admin' in prev_frame_face_names and 'admin' not in face_names
                , 'admin' not in prev_frame_face_names and 'admin' in face_names
                , prev_frame_face_names is None]
            output = ['User Left', 'User Returned', 'First Frame']
            line_of_sight = np.select(conditions, output, default='No Change').item(0)

            prev_frame_face_names = face_names

            if line_of_sight == 'User Left':
                LockScreen()
            elif line_of_sight == 'User Returned':
                UnlockScreen()
            else:
                pass

            #     switch (line_of_sight) {
            #         case "User Left":  LockScreen();
            #         break;
            #         case "User Returned": UnlockScreen();
            #         break;
            #         case "No Change": pass;
            #         break;
            #     }

            print("read frame")

        else:
            print("couldn't read frame")

        print(face_names)
        print(prev_frame_face_names)
        print(line_of_sight)

        k = cv2.waitKey(1)
        if k % 256 == 27:
            # ESC pressed
            print("Escape hit, closing...")
            video_capture.release()
            cv2.destroyAllWindows()
            break

    # video_capture.release()
    # cv2.destroyAllWindows()


os.system("unset HISTFILE") # temporarily disable bash history
if not CHECK_FOLDER:
    Setup() # If folder doesn't exist, then go through initial set up steps.
else:
    Sentry() # Otherwise monitor



