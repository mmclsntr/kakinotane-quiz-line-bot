import cv2
import numpy as np
import random


# 画像にシャドウを追加する関数
def add_shadow(image):
    alpha = image[:, :, 3]/255
    alpha = alpha[:, :, np.newaxis]  # alphaを3次元配列に変換
    shadow = cv2.GaussianBlur(image[:, :, :3], (15, 15), 0)
    image[:, :, :3] = alpha * image[:, :, :3] + (1 - alpha) * shadow
    return image

# 画像をランダムに回転させる関数
def rotate_image(image):
    angle = random.randint(0,360)
    angle_rad = angle/180.0*np.pi
    h, w = image.shape[:2]

    # 回転後の画像サイズを計算
    w_rot = int(np.round(h*np.absolute(np.sin(angle_rad))+w*np.absolute(np.cos(angle_rad))))
    h_rot = int(np.round(h*np.absolute(np.cos(angle_rad))+w*np.absolute(np.sin(angle_rad))))
    size_rot = (w_rot, h_rot)

    # 元画像の中心を軸に回転する
    center = (w/2, h/2)
    scale = 1.0
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, scale)

    # 平行移動を加える (rotation + translation)
    affine_matrix = rotation_matrix.copy()
    affine_matrix[0][2] = affine_matrix[0][2] -w/2 + w_rot/2
    affine_matrix[1][2] = affine_matrix[1][2] -h/2 + h_rot/2

    rotated_image = cv2.warpAffine(image, affine_matrix, size_rot)
    return rotated_image

# 透過画像を背景に配置する関数
def place_image(background, img, x, y):
    #img = rotate_image(img)  # 画像回転
    h, w, _ = img.shape
    alpha = img[:, :, 3]/255
    for c in range(3):
        background[y:y+h, x:x+w, c] = alpha * img[:, :, c] + (1 - alpha) * background[y:y+h, x:x+w, c]
    return background

# 画像をランダムに配置する関数
def place_images_randomly(background, img, n):
    bh, bw, _ = background.shape
    for _ in range(n):
        img_rot = rotate_image(img)
        h_rot, w_rot, _ = img_rot.shape
        x = random.randint(0, bw - w_rot)
        y = random.randint(0, bh - h_rot)
        background = place_image(background, img_rot, x, y)
    return background


def create_kakinotane_image(ratio: float,
                            output_file_name: str = "output.jpg",
                            kakinotane_img_file_name: str = "kakinotane_photo.png",
                            peanut_img_file_name: str = "peanut_photo.png",
                            ):
    # 画像の読み込み
    img_a = cv2.imread(kakinotane_img_file_name, cv2.IMREAD_UNCHANGED)
    img_b = cv2.imread(peanut_img_file_name, cv2.IMREAD_UNCHANGED)

    # 画像のリサイズ
    img_a = cv2.resize(img_a, (img_a.shape[1] // 4, img_a.shape[0] // 4))
    img_b = cv2.resize(img_b, (img_b.shape[1] // 4, img_b.shape[0] // 4))

    # シャドウの追加
    #img_a = add_shadow(img_a)
    #img_b = add_shadow(img_b)

    # 白背景画像の作成
    background = np.ones((1000, 1000, 3), np.uint8) * 255

    # 配置する回数を計算
    n_total = (background.shape[0]//img_a.shape[0]) * (background.shape[1]//img_a.shape[1])

    # 画像aとbの配置比率を設定
    ratio_a = ratio
    ratio_b = 1 - ratio_a

    # 配置する回数を計算
    n_a = round(n_total * ratio_a)
    n_b = n_total - n_a

    # 画像をランダムに配置
    for i in range(3):
        # N回する。
        background = place_images_randomly(background, img_a, n_a)
        background = place_images_randomly(background, img_b, n_b)

    cv2.imwrite(output_file_name, background)

    # 結果を表示
    #cv2.imshow('Image', background)
    #cv2.waitKey(0)
    #cv2.destroyAllWindows()


if __name__ == "__main__":
    create_kakinotane_image(0.8)
