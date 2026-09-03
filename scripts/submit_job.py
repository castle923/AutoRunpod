import json, sys, os, subprocess

def main():
    character_prompt = sys.argv[1]
    n_iter = int(sys.argv[2])
    batch_size = int(sys.argv[3])
    tag = sys.argv[4]  # for log file naming

    with open("/workspace/dynamic_prompts/costume_pose_expression_combined.txt", encoding="utf-8") as f:
        dynamic_prompt = f.read()

    full_prompt = character_prompt.rstrip("\n") + "\n\n" + dynamic_prompt

    negative_prompt = "lowres, (bad), text, error, fewer, extra, missing, worst quality, jpeg artifacts, low quality, watermark, unfinished, displeasing, oldest, early, chromatic aberration, signature, extra digits, artistic error, username, scan, large areolae, (thick thighs:1.4), ribs,"

    payload = {
        "prompt": full_prompt,
        "negative_prompt": negative_prompt,
        "seed": -1,
        "sampler_name": "Euler a",
        "scheduler": "sgm_uniform",
        "batch_size": batch_size,
        "n_iter": n_iter,
        "steps": 30,
        "cfg_scale": 5,
        "width": 896,
        "height": 1152,
        "denoising_strength": 0.35,
        "enable_hr": True,
        "hr_scale": 1.5,
        "hr_second_pass_steps": 15,
        "hr_upscaler": "R-ESRGAN 4x+ Anime6B",
        "hr_prompt": full_prompt,
        "hr_negative_prompt": negative_prompt,
    }

    payload_path = f"/workspace/payload_{tag}.json"
    with open(payload_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)

    log_path = f"/workspace/gen_{tag}.log"
    cmd = (
        f'setsid bash -c \'curl -sS -X POST "https://wwq5sg4yyafg6o-3000.proxy.runpod.net/sdapi/v1/txt2img" '
        f'-H "Content-Type: application/json" -d @{payload_path} > {log_path} 2>&1; '
        f'echo SUBMIT_DONE_EXIT=$? >> {log_path}\' < /dev/null > /dev/null 2>&1 &'
    )
    subprocess.run(cmd, shell=True)
    print("submitted job tag=%s n_iter=%d batch_size=%d, log=%s" % (tag, n_iter, batch_size, log_path))

if __name__ == "__main__":
    main()
