import { useState } from "react";

/** Text input with a send button; disabled while a tutor response is streaming. */
function TutorInput({ onSend, disabled }) {
  const [value, setValue] = useState("");

  function submit(event) {
    event.preventDefault();
    if (!value.trim() || disabled) return;
    onSend(value);
    setValue("");
  }

  return (
    <form onSubmit={submit}>
      <input
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder="Defend your answer..."
        disabled={disabled}
      />
      <button disabled={disabled}>Send</button>
    </form>
  );
}

export default TutorInput;
