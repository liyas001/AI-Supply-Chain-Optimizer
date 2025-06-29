from llama_cpp import Llama

llama = Llama(
    model_path = r"C:\Users\liyas\PycharmProjects\PythonProject1\models\llama-2-7b-chat.Q4_K_M.gguf",
    n_ctx=2048,
    n_threads=8,
    n_gpu_layers=35
)


def ask_local_ai(question):
    response = llama.create_chat_completion(
        messages=[{"role": "user", "content": question}]
    )
    return response['choices'][0]['message']['content']

