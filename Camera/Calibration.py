import cv2
import os
import numpy as np

CAMERA_INDEX = 1  # ou 0 selon le port


def capture_mire_images():
    output_dir = "calib_images"
    
    # 1. Creer le dossier d'enregistrement
    try:
        os.makedirs(output_dir, exist_ok=True)
        print(f"Dossier '{output_dir}' pret.")
    except Exception as e:
        print("Erreur lors de la creation du dossier :", e)
        return

    # 2. Connexion a la camera
    try:
        cap = cv2.VideoCapture(CAMERA_INDEX)
        if not cap.isOpened():
            raise IOError("Impossible d'ouvrir la camera.")
        print("Camera ouverte avec succes.")
    except Exception as e:
        print("Erreur lors de l'ouverture de la camera :", e)
        return

    count = 0
    max_images = 20

    print("Instructions :")
    print("- Appuie sur ESPACE pour capturer une image")
    print("- Appuie sur ECHAP pour quitter")

    try:
        while count < max_images:
            ret, frame = cap.read()
            if not ret:
                print("Erreur lors de la capture.")
                break

            display = frame.copy()
            cv2.putText(display, f"Image {count+1}/{max_images}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            cv2.imshow("Capture mire", display)
            key = cv2.waitKey(1) & 0xFF

            if key == 27:  # ECHAP
                print("Capture interrompue.")
                break
            elif key == 32:  # ESPACE
                filename = os.path.join(output_dir, f"calib_image{count+1}.jpg")
                try:
                    cv2.imwrite(filename, frame)
                    print(f"Image {count+1} enregistree : {filename}")
                    count += 1
                except Exception as e:
                    print("Erreur lors de la sauvegarde de l'image :", e)
                    break
    except Exception as e:
        print("Erreur pendant la boucle de capture :", e)
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("Camera liberee. Fenetres fermees.")



def calibrate_camera(images_folder, pattern_size=(9, 6), square_size=25.0):
    objp = np.zeros((pattern_size[1]*pattern_size[0], 3), np.float32)
    objp[:, :2] = np.mgrid[0:pattern_size[0], 0:pattern_size[1]].T.reshape(-1, 2)
    objp *= square_size

    objpoints = []
    imgpoints = []
    
    image_files = sorted([
        os.path.join(images_folder, f)
        for f in os.listdir(images_folder)
        if f.endswith((".jpg", ".png"))
    ])

    for fname in image_files:
        img = cv2.imread(fname)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ret, corners = cv2.findChessboardCorners(gray, pattern_size, None)

        if ret:
            objpoints.append(objp)
            imgpoints.append(corners)
            cv2.drawChessboardCorners(img, pattern_size, corners, ret)
            cv2.imshow("Coins detectes", img)
            cv2.waitKey(300)

    cv2.destroyAllWindows()

    ret, K, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)
    return K, dist

def estimate_camera_pose(K, dist, image, img_pts, obj_pts):
    img_pts = np.array(img_pts, dtype=np.float32)
    obj_pts = np.array(obj_pts, dtype=np.float32)

    success, rvec, tvec = cv2.solvePnP(obj_pts, img_pts, K, dist)
    R, _ = cv2.Rodrigues(rvec)
    return R, tvec, rvec

def draw_detected_points(image, points, color=(0, 255, 0)):
    for pt in points:
        cv2.circle(image, tuple(int(x) for x in pt), 8, color, -1)
    return image

def calibrate_and_estimate_pose():
    calib_folder = "calib_images"
    pattern_size = (9, 6)  # 9x6 inner corners = 10x7 squares
    square_size = 25.0     # mm

    try:
        print("Calibration en cours...")
        K, dist = calibrate_camera(calib_folder, pattern_size, square_size)
        print("Calibration terminee.")
        print("Matrice K :\n", K)
        print("Distortion :\n", dist)
    except Exception as e:
        print("Erreur lors de la calibration :", e)
        return

    # Exemple de 4 coins detectes automatiquement dans l'image
    print("Connexion a la camera...")
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("Impossible d'ouvrir la camera.")
        return

    ret, frame = cap.read()
    cap.release()
    if not ret:
        print("Erreur lors de la capture de l'image.")
        return

    # >> A ADAPTER : remplacer ceci par ton detecteur automatique de 4 coins <<
    # Ici : exemple manuel de 4 points en pixels (image)
    img_pts = [(150, 150), (450, 150), (450, 450), (150, 450)]  # pixels
    # Et leurs correspondants dans le repere robot (en mm)
    obj_pts = [(300, 300, 0), (500, 300, 0), (500, 500, 0), (300, 500, 0)]

    frame_visu = draw_detected_points(frame.copy(), img_pts)

    try:
        R, t, rvec = estimate_camera_pose(K, dist, frame, img_pts, obj_pts)
        print("Matrice de rotation R :\n", R)
        print("Vecteur de translation t :\n", t)
    except Exception as e:
        print("Erreur lors du calcul de la pose :", e)
        return

    cv2.imshow("Points detectes", frame_visu)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    try:
        np.savez("params_camera.npz",
                 camera_matrix=K,
                 dist_coeffs=dist,
                 rvec=rvec,
                 tvec=t,
                 rotation_matrix=R)
        print("Parametres sauvegardes dans 'params_camera.npz'")
    except Exception as e:
        print("Erreur lors de la sauvegarde :", e)

if __name__ == "__main__":
    capture_mire_images()

    input("Appuie sur Entree pour lancer la calibration...")

    calibrate_and_estimate_pose()

