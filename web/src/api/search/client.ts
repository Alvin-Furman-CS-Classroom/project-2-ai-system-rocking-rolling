import type { paths, operations } from "./schema";
import createFetchClient from "openapi-fetch";
import createClient from "openapi-react-query";

export type SongSearchResult =
	operations["getSearchSongs"]["responses"]["200"]["content"]["application/json"][number];

export const fetchClient = createFetchClient<paths>({
	baseUrl: "/song-api",
});

export const $api = createClient(fetchClient);
