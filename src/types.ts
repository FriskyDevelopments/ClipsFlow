export interface Clip {
  id: string;
  title: string;
  filePath: string;
  durationSeconds: number;
  tags: string[];
  createdAt: string;
  updatedAt: string;
}

export interface CreateClipInput {
  title: string;
  filePath: string;
  durationSeconds: number;
  tags?: string[];
}

export interface UpdateClipInput {
  title?: string;
  tags?: string[];
}

export interface ClipQuery {
  tag?: string;
  page?: number;
  limit?: number;
}
