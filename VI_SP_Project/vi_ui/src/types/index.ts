export type Department = {
    name: string;
    link?: string;
    location: {
        lat: number | null;
        lon: number | null;
    };
};

export type University = {
    institution: string;
    name: string;
    partner?: string;
    link?: string;
    location?: {
        lat: number | null;
        lon: number | null;
    };
    departments?: Department[];
};

export type IEPartner = {
    uni_name: string;
    dept_name: string;
    link: string;
    lat: number | null;
    lon: number | null;
};

export type IEPartnerCountry = {
    country: string;
    country_code: string;
    partners: IEPartner[];
};

export type SearchResult = {
    countryCode: string;
    uni?: University;
    dept?: Department;
    iePartner?: IEPartner;
    isIEPartner: boolean;
};

export type TopicData = {
    country: string;
    topic: string;
    type: string;
    count: number;
    subtopics: Record<string, number>;
};

export type ParsedDataDictionary = Record<string, TopicData[]>;

export type ModalPayload = {
    title: string;
    subtitle: string;
    data: TopicData[];
};