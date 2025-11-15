# recognition_engine.py
import os
import numpy as np
import torch
import cv2
from facenet_pytorch import InceptionResnetV1

UNKNOWN_NAME = "Unknown"

class RecognitionEngine:
    """
    Face embedding & recognition với FaceNet (InceptionResnetV1, vggface2).
    Cung cấp: embed_batch, add_face, predict_batch, save_db, load_db
    """
    def __init__(self, device="cuda" if torch.cuda.is_available() else "cpu",
                 recog_thres=0.60, face_margin=0.15, out_size=160):
        self.device = device
        self.model = InceptionResnetV1(pretrained='vggface2').eval().to(self.device)
        self.embs = None  # (N, 512) float32 L2-normalized
        self.names = []   # list[str]
        self.recog_thres = float(recog_thres)
        self.face_margin = float(face_margin)
        self.out_size = int(out_size)

    def set_threshold(self, thres: float):
        self.recog_thres = float(thres)

    @staticmethod
    def _safe_int(v): return int(max(0, v))

    def _preprocess_crop(self, bgr, box):
        h, w = bgr.shape[:2]
        x1, y1, x2, y2 = [int(v) for v in box]
        bw, bh = x2 - x1, y2 - y1
        mx = self._safe_int(bw * self.face_margin)
        my = self._safe_int(bh * self.face_margin)
        x1 = max(0, x1 - mx); y1 = max(0, y1 - my)
        x2 = min(w, x2 + mx); y2 = min(h, y2 + my)
        crop = bgr[y1:y2, x1:x2]
        if crop.size == 0:
            return None
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        rgb = cv2.resize(rgb, (self.out_size, self.out_size))
        t = torch.from_numpy(rgb).permute(2, 0, 1).float() / 255.0
        t = (t - 0.5) / 0.5
        return t

    def embed_batch(self, bgr, boxes):
        tensors, valid_idx = [], []
        for i, box in enumerate(boxes):
            t = self._preprocess_crop(bgr, box)
            if t is not None:
                tensors.append(t); valid_idx.append(i)
        if not tensors:
            return None, []
        batch = torch.stack(tensors).to(self.device)
        with torch.no_grad():
            emb = self.model(batch).cpu().numpy().astype('float32')  # (B,512)
        emb /= (np.linalg.norm(emb, axis=1, keepdims=True) + 1e-9)
        return emb, valid_idx

    def add_face(self, name, emb_vec):
        emb = emb_vec.astype('float32')
        emb /= (np.linalg.norm(emb) + 1e-9)
        if self.embs is None:
            self.embs = emb[None, :]
            self.names = [name]
        else:
            self.embs = np.vstack([self.embs, emb[None, :]])
            self.names.append(name)

    def predict_batch(self, embs):
        if self.embs is None or len(self.names) == 0:
            return [UNKNOWN_NAME] * len(embs), [0.0] * len(embs)
        sims = embs @ self.embs.T
        idxs = np.argmax(sims, axis=1)
        smax = sims[np.arange(len(embs)), idxs]
        names = [self.names[i] if s >= self.recog_thres else UNKNOWN_NAME
                 for i, s in zip(idxs, smax)]
        return names, [float(s) for s in smax]

    def save_db(self, path):
        if self.embs is None or not self.names:
            raise RuntimeError("DB trống.")
        np.savez_compressed(path, embs=self.embs, names=np.array(self.names, dtype=object))

    def load_db(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        data = np.load(path, allow_pickle=True)
        self.embs = data["embs"].astype('float32')
        self.names = list(data["names"].tolist())


def iou_xyxy(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    inter_x1, inter_y1 = max(ax1, bx1), max(ay1, by1)
    inter_x2, inter_y2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, inter_x2 - inter_x1), max(0, inter_y2 - inter_y1)
    inter = iw * ih
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union = area_a + area_b - inter + 1e-6
    return inter / union
