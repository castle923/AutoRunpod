# 포드 설정 파일

## nginx.conf

RunPod 기본 이미지의 `/etc/nginx/nginx.conf`에 **Gradio 4.x SSE 전용 블록을 추가한
버전**이다. 새 포드에서는 `bootstrap_pod.sh`가 자동으로 배치한다.

추가한 부분은 `location /queue/data` 하나다:

```nginx
location /queue/data {
    proxy_buffering off;
    proxy_set_header Accept-Encoding "";
    proxy_read_timeout 3600;
    gzip off;
    ...
}
```

기본 `location /` 블록은 `Accept-Encoding gzip`을 강제하고 버퍼링을 켜두기 때문에,
Gradio가 결과를 전달하는 SSE 스트림이 플러시되지 않는다. 이 블록이 없으면 생성은
정상적으로 끝나는데 브라우저에는 결과가 도착하지 않는 상태가 될 수 있다.

**중요**: `/etc/nginx/`는 `/workspace` 영구 볼륨 밖이라 컨테이너가 재생성되면
이 수정이 사라진다. 그래서 저장소에 원본을 두고 부트스트랩이 다시 배치한다.

## config.json / ui-config.json

Forge의 UI·생성 기본값. 저장소 루트의 것을 부트스트랩이
`/workspace/stable-diffusion-webui-forge/`에 배치한다.
