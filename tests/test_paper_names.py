"""The names of the papers a question names, as the answer model lists them (#81)."""

from chatbot_rag_tokenizers.chat.names import name_papers

PROMPT = "List the papers the question names."
QUESTION = "Does Rényi efficiency predict performance? Compare Zouhar et al.'s results with Tokenization Is More Than Compression."


def test_the_model_is_asked_with_the_names_prompt_and_the_question_alone(fake_answer_model):
    fake_answer_model.script[QUESTION] = "Zouhar et al.\nTokenization Is More Than Compression"

    assert name_papers(fake_answer_model, PROMPT, QUESTION) == ("Zouhar et al.", "Tokenization Is More Than Compression")
    assert fake_answer_model.chats == [[{"role": "system", "content": PROMPT}, {"role": "user", "content": QUESTION}]]


def test_only_names_the_question_holds_are_kept_once_without_list_markers(fake_answer_model):
    # The 2B model invents methods a question never names ("Attention Is All You Need"), and numbers or bullets its lines.
    fake_answer_model.script[QUESTION] = (
        "1. Rényi efficiency\n- zouhar et al.\n* Attention Is All You Need\n\"Tokenization Is More Than Compression\"\nRényi efficiency"
    )

    assert name_papers(fake_answer_model, PROMPT, QUESTION) == ("Rényi efficiency", "zouhar et al.", "Tokenization Is More Than Compression")


def test_none_names_nothing(fake_answer_model):
    fake_answer_model.script["What multiple"] = "NONE"

    assert name_papers(fake_answer_model, PROMPT, "What multiple of the English bill could non-English speakers face?") == ()
