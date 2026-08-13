from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .services import compare_pronunciation, speech_to_text, text_to_speech


@require_GET
def tts_view(request):
    text = request.GET.get("text", "")
    lang = request.GET.get("lang", "en")
    slow = request.GET.get("slow", "").lower() in ("1", "true", "yes")
    voice = request.GET.get("voice", "")
    if not text:
        raise Http404
    path = text_to_speech(text, lang, slow=slow, voice=voice)
    if not path:
        raise Http404
    return FileResponse(open(path, "rb"), content_type="audio/mpeg")


@csrf_exempt
@require_POST
def stt_view(request):
    audio = request.FILES.get("audio")
    if not audio:
        return JsonResponse({"error": "No audio"}, status=400)
    text = speech_to_text(audio.read())
    return JsonResponse({"text": text})


@csrf_exempt
@require_POST
def pronunciation_check(request):
    spoken = request.POST.get("spoken", "")
    expected = request.POST.get("expected", "")
    if not expected:
        return JsonResponse({"error": "No expected text"}, status=400)
    if not spoken and request.FILES.get("audio"):
        spoken = speech_to_text(request.FILES["audio"].read())
    result = compare_pronunciation(spoken, expected)
    return JsonResponse(result)
