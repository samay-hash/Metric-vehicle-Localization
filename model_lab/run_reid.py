"""Vehicle-trained FastReID inference; similarities are review candidates, not identities."""
import argparse
import json
import sys
import time
from pathlib import Path
from common import ROOT, MODELS, RUNS, save_json, sha256


def load_model(device):
    import torch
    sys.path.insert(0, str(ROOT / 'vendor/fast-reid'))
    from fastreid.config import get_cfg
    from fastreid.modeling import build_model
    cfg = get_cfg()
    cfg.merge_from_file(str(ROOT / 'vendor/fast-reid/configs/VeRi/sbs_R50-ibn.yml'))
    cfg.MODEL.DEVICE = device
    cfg.MODEL.BACKBONE.PRETRAIN = False
    cfg.MODEL.HEADS.NUM_CLASSES = 575
    model = build_model(cfg)
    state = torch.load(MODELS / 'veri_sbs_R50-ibn.pth', map_location='cpu', weights_only=True)['model']
    # Official v0.1.1 checkpoint predates current head naming. The classifier isn't
    # used at inference, but mapping it permits strict validation of its dimensions.
    state['heads.weight'] = state.pop('heads.classifier.weight')
    state.pop('heads.bnneck.num_batches_tracked', None)
    for name, buffer in [('pixel_mean', model.pixel_mean), ('pixel_std', model.pixel_std)]:
        source = state.pop(name)
        if not torch.allclose(source.reshape_as(buffer).cpu(), buffer.cpu()):
            raise ValueError(f'Checkpoint preprocessing mismatch: {name}')
    missing, unexpected = model.load_state_dict(state, strict=False)
    real_missing = [k for k in missing if not k.endswith('num_batches_tracked')]
    if real_missing or unexpected:
        raise RuntimeError(f'Checkpoint mismatch: missing={real_missing}, unexpected={unexpected}')
    return model.eval(), tuple(cfg.INPUT.SIZE_TEST)


def main():
    import cv2
    import numpy as np
    import torch
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, default=RUNS / 'nano')
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--max-crops', type=int, default=100)
    args = parser.parse_args()
    torch.set_num_threads(2)
    model, (height, width) = load_model(args.device)
    records, vectors = [], []
    seen = set()
    for line in (args.run / 'detections.jsonl').read_text().splitlines():
        frame = json.loads(line)
        for vehicle in frame['vehicles']:
            key = (frame['camera_id'], vehicle['track_id'])
            if vehicle['track_id'] is not None and key in seen:
                continue
            seen.add(key)
            crop = cv2.imread(str(args.run / vehicle['crop']))
            rgb = cv2.cvtColor(cv2.resize(crop, (width,height), interpolation=cv2.INTER_CUBIC), cv2.COLOR_BGR2RGB)
            tensor = torch.from_numpy(rgb.transpose(2,0,1).copy()).float().unsqueeze(0).to(args.device)
            start = time.perf_counter()
            with torch.inference_mode():
                embedding = torch.nn.functional.normalize(model(tensor), dim=1).cpu().numpy()[0]
            records.append({'vehicle_id': vehicle['id'], 'camera_id': frame['camera_id'],
                            'track_id': vehicle['track_id'], 'crop': vehicle['crop'],
                            'latency_ms': (time.perf_counter()-start)*1000})
            vectors.append(embedding)
            if len(vectors) >= args.max_crops:
                break
        if len(vectors) >= args.max_crops:
            break
    if vectors:
        matrix = np.stack(vectors)
        if not np.isfinite(matrix).all():
            raise ValueError('ReID returned non-finite values')
        np.save(args.run / 'reid_embeddings.npy', matrix)
        similarities = matrix @ matrix.T
        for i, record in enumerate(records):
            candidates = [j for j in np.argsort(-similarities[i])
                          if records[j]['camera_id'] != record['camera_id']][:3]
            record['cross_camera_appearance_candidates'] = [
                {'vehicle_id': records[j]['vehicle_id'], 'cosine_similarity': float(similarities[i,j]),
                 'status': 'unverified_appearance_only'} for j in candidates]
    save_json(args.run / 'reid.json', {'model': 'FastReID VeRi SBS R50-IBN',
              'weights_sha256': sha256(MODELS/'veri_sbs_R50-ibn.pth'),
              'input': 'RGB 0..255, 256x256 bicubic; checkpoint mean/std applied in model',
              'device': args.device, 'embedding_dim': len(vectors[0]) if vectors else None,
              'observations': records, 'identity_accuracy': None,
              'note': 'Appearance similarity alone does not confirm identity. No ground-truth cross-camera pairs supplied.'})
    print(f'ReID: {len(records)} vehicle embeddings', flush=True)


if __name__ == '__main__':
    main()
