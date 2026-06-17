import {Composition, Folder} from 'remotion';
import {PipelineDelivery, PipelineGuardrails, PipelineIntake} from './PipelineAnimations';

export const RemotionRoot = () => {
  return (
    <Folder name="ClipsFlow-Pipeline">
      <Composition
        id="PipelineIntake"
        component={PipelineIntake}
        durationInFrames={360}
        fps={30}
        width={1080}
        height={1080}
      />
      <Composition
        id="PipelineGuardrails"
        component={PipelineGuardrails}
        durationInFrames={360}
        fps={30}
        width={1080}
        height={1080}
      />
      <Composition
        id="PipelineDelivery"
        component={PipelineDelivery}
        durationInFrames={360}
        fps={30}
        width={1080}
        height={1080}
      />
    </Folder>
  );
};
