class PCMProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
    }

    process(inputs, outputs, parameters) {
        const input = inputs[0];
        if (!input || input.length === 0) return true;

        // input is an array of Float32Arrays (one per channel)
        const inputL = input[0];
        const inputR = input.length > 1 ? input[1] : inputL;

        const length = inputL.length;
        // Create Int16Array for interleaved PCM
        const pcmData = new Int16Array(length * 2);

        let pcmIndex = 0;
        for (let i = 0; i < length; i++) {
            // Channel L
            let sL = Math.max(-1, Math.min(1, inputL[i]));
            pcmData[pcmIndex++] = sL < 0 ? sL * 0x8000 : sL * 0x7FFF;

            // Channel R
            let sR = Math.max(-1, Math.min(1, inputR[i]));
            pcmData[pcmIndex++] = sR < 0 ? sR * 0x8000 : sR * 0x7FFF;
        }

        // Post data back to main thread
        this.port.postMessage(pcmData.buffer, [pcmData.buffer]);

        return true;
    }
}

registerProcessor('pcm-processor', PCMProcessor);
