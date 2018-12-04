/////////////////////////////////////////////////////////////////////////
///@author ��̩֤ȯ�ɷ����޹�˾
///@file xtp_api_data_type.h
///@brief ����������ݻ�������
/////////////////////////////////////////////////////////////////////////
#ifndef _XTP_API_DATA_TYPE_H_
#define _XTP_API_DATA_TYPE_H_

#pragma pack(8)

/// ��Ű汾�ŵ��ַ�������
#define XTP_VERSION_LEN 16
/// �汾������
typedef char XTPVersionType[XTP_VERSION_LEN];
/// �ɽ������ַ�������
#define XTP_TRADING_DAY_LEN 9
/// ���֤ȯ������ַ�������
#define XTP_TICKER_LEN 16
/// ���֤ȯ���Ƶ��ַ�������
#define XTP_TICKER_NAME_LEN 64
/// ���ر�����ŵ��ַ�������
#define XTP_LOCAL_ORDER_LEN         11
/// ���������ŵ��ַ�������
#define XTP_ORDER_EXCH_LEN          17
/// �ɽ�ִ�б�ŵ��ַ�������
#define XTP_EXEC_ID_LEN             18
/// ����������Ա�����ַ�������
#define XTP_BRANCH_PBU_LEN          7
/// �û��ʽ��˻����ַ�������
#define XTP_ACCOUNT_NAME_LEN        16

/////////////////////////////////////////////////////////////////////////
///@enum XTP_LOG_LEVEL ����־�����������
/////////////////////////////////////////////////////////////////////////
enum XTP_LOG_LEVEL {
	XTP_LOG_LEVEL_FATAL, ///<���ش��󼶱�
	XTP_LOG_LEVEL_ERROR, ///<���󼶱�
	XTP_LOG_LEVEL_WARNING, ///<���漶��
	XTP_LOG_LEVEL_INFO,   ///<info����
	XTP_LOG_LEVEL_DEBUG,  ///<debug����
	XTP_LOG_LEVEL_TRACE   ///<trace����
};

/////////////////////////////////////////////////////////////////////////
///@enum XTP_PROTOCOL_TYPE ��ͨѶ����Э�鷽ʽ
/////////////////////////////////////////////////////////////////////////
enum XTP_PROTOCOL_TYPE
{
	XTP_PROTOCOL_TCP = 1,	///<����TCP��ʽ����
	XTP_PROTOCOL_UDP		///<����UDP��ʽ���䣨Ŀǰ��δ֧�֣�
};



/////////////////////////////////////////////////////////////////////////
///@enum XTP_EXCHANGE_TYPE �ǽ���������
/////////////////////////////////////////////////////////////////////////
enum XTP_EXCHANGE_TYPE
{
	XTP_EXCHANGE_SH = 1,	///<��֤
	XTP_EXCHANGE_SZ,		///<��֤
    XTP_EXCHANGE_UNKNOWN	///<�����ڵĽ���������
};

//////////////////////////////////////////////////////////////////////////
///@enum XTP_MARKET_TYPE �г�����
//////////////////////////////////////////////////////////////////////////
enum XTP_MARKET_TYPE
{
    XTP_MKT_INIT = 0,///<��ʼ��ֵ����δ֪
    XTP_MKT_SZ_A = 1,///<����A��
    XTP_MKT_SH_A,    ///<�Ϻ�A��
    XTP_MKT_UNKNOWN   ///<δ֪�����г�����
};


/////////////////////////////////////////////////////////////////////////
///@enum XTP_PRICE_TYPE �Ǽ۸�����
/////////////////////////////////////////////////////////////////////////
enum XTP_PRICE_TYPE
{
    XTP_PRICE_LIMIT = 1,           ///<�޼۵�-�������ͨ��Ʊҵ���⣬����ҵ���ʹ�ô������ͣ�
    XTP_PRICE_BEST_OR_CANCEL,      ///<��ʱ�ɽ�ʣ��ת�������м۵�-��
    XTP_PRICE_BEST5_OR_LIMIT,      ///<�����嵵��ʱ�ɽ�ʣ��ת�޼ۣ��м۵�-��
    XTP_PRICE_BEST5_OR_CANCEL,     ///<����5����ʱ�ɽ�ʣ��ת�������м۵�-����
    XTP_PRICE_ALL_OR_CANCEL,       ///<ȫ���ɽ�����,�м۵�-��
    XTP_PRICE_FORWARD_BEST,        ///<�������ţ��м۵�-��
    XTP_PRICE_REVERSE_BEST_LIMIT,  ///<�Է�����ʣ��ת�޼ۣ��м۵�-��
    XTP_PRICE_TYPE_UNKNOWN,		   ///<δ֪������Ч�۸�����
};



/////////////////////////////////////////////////////////////////////////
///@enum XTP_SIDE_TYPE ��������������
/////////////////////////////////////////////////////////////////////////
enum XTP_SIDE_TYPE
{
	XTP_SIDE_BUY = 1,	///<���¹��깺��ETF�깺�ȣ�
	XTP_SIDE_SELL,		///<������ع���
	XTP_SIDE_BUY_OPEN,		///<�򿪣���δ֧�֣�
	XTP_SIDE_SELL_OPEN,		///<��������δ֧�֣�
	XTP_SIDE_BUY_CLOSE,		///<��ƽ����δ֧�֣�
	XTP_SIDE_SELL_CLOSE,	///<��ƽ����δ֧�֣�
	XTP_SIDE_PURCHASE,		///<�깺����δ֧�֣�
	XTP_SIDE_REDEMPTION,	///<��أ���δ֧�֣�
	XTP_SIDE_SPLIT,			///<��֣���δ֧�֣�
	XTP_SIDE_MERGE,			///<�ϲ�����δ֧�֣�
    XTP_SIDE_UNKNOWN		///<δ֪������Ч��������
};

/////////////////////////////////////////////////////////////////////////
///@enum XTP_ORDER_ACTION_STATUS_TYPE �Ǳ�������״̬����
/////////////////////////////////////////////////////////////////////////
enum XTP_ORDER_ACTION_STATUS_TYPE
{
	XTP_ORDER_ACTION_STATUS_SUBMITTED = 1,	///<�Ѿ��ύ
	XTP_ORDER_ACTION_STATUS_ACCEPTED,		///<�Ѿ�����
	XTP_ORDER_ACTION_STATUS_REJECTED		///<�Ѿ����ܾ�
};

/////////////////////////////////////////////////////////////////////////
///@enum XTP_ORDER_STATUS_TYPE �Ǳ���״̬����
/////////////////////////////////////////////////////////////////////////
enum XTP_ORDER_STATUS_TYPE
{
    XTP_ORDER_STATUS_INIT = 0,///<��ʼ��
    XTP_ORDER_STATUS_ALLTRADED = 1,           ///<ȫ���ɽ�
    XTP_ORDER_STATUS_PARTTRADEDQUEUEING,  ///<���ֳɽ�
    XTP_ORDER_STATUS_PARTTRADEDNOTQUEUEING, ///<���ֳ���
    XTP_ORDER_STATUS_NOTRADEQUEUEING,   ///<δ�ɽ�
    XTP_ORDER_STATUS_CANCELED,  ///<�ѳ���
    XTP_ORDER_STATUS_REJECTED,  ///<�Ѿܾ�
    XTP_ORDER_STATUS_UNKNOWN  ///<δ֪����״̬
};

/////////////////////////////////////////////////////////////////////////
///@enum XTP_ORDER_SUBMIT_STATUS_TYPE �Ǳ����ύ״̬����
/////////////////////////////////////////////////////////////////////////
enum XTP_ORDER_SUBMIT_STATUS_TYPE
{
    XTP_ORDER_SUBMIT_STATUS_INSERT_SUBMITTED = 1, ///<�����Ѿ��ύ
    XTP_ORDER_SUBMIT_STATUS_INSERT_ACCEPTED,///<�����Ѿ�������
    XTP_ORDER_SUBMIT_STATUS_INSERT_REJECTED,///<�����Ѿ����ܾ�
    XTP_ORDER_SUBMIT_STATUS_CANCEL_SUBMITTED,///<�����Ѿ��ύ
    XTP_ORDER_SUBMIT_STATUS_CANCEL_REJECTED,///<�����Ѿ����ܾ�
    XTP_ORDER_SUBMIT_STATUS_CANCEL_ACCEPTED ///<�����Ѿ�������
};


/////////////////////////////////////////////////////////////////////////
///@enum XTP_TE_RESUME_TYPE �ǹ�������������Ӧ���ɽ��ر����ش���ʽ
/////////////////////////////////////////////////////////////////////////
enum XTP_TE_RESUME_TYPE
{
	XTP_TERT_RESTART = 0,	///<�ӱ������տ�ʼ�ش�
	XTP_TERT_RESUME,		///<�Ӵ��ϴ��յ�����������δ֧�֣�
	XTP_TERT_QUICK			///<ֻ���͵�¼��������������Ӧ���ɽ��ر���������
};



//////////////////////////////////////////////////////////////////////////
///@enum XTP_TICKER_TYPE ֤ȯ����
//////////////////////////////////////////////////////////////////////////
enum XTP_TICKER_TYPE
{
	XTP_TICKER_TYPE_STOCK = 0,            ///<��ͨ��Ʊ
	XTP_TICKER_TYPE_INDEX,                ///<ָ��
	XTP_TICKER_TYPE_FUND,                 ///<����
	XTP_TICKER_TYPE_BOND,                 ///<ծȯ
	XTP_TICKER_TYPE_UNKNOWN               ///<δ֪����
	
};

//////////////////////////////////////////////////////////////////////////
///@enum XTP_BUSINESS_TYPE ֤ȯҵ������
//////////////////////////////////////////////////////////////////////////
enum XTP_BUSINESS_TYPE
{
	XTP_BUSINESS_TYPE_CASH = 0,            ///<��ͨ��Ʊҵ�񣨹�Ʊ������ETF�����ȣ�
	XTP_BUSINESS_TYPE_IPOS,                ///<�¹��깺ҵ�񣨶�Ӧ��price type��ѡ���޼����ͣ�
	XTP_BUSINESS_TYPE_REPO,                ///<�ع�ҵ�� ( ��Ӧ��price type��Ϊ�޼ۣ�side��Ϊ�� )
	XTP_BUSINESS_TYPE_ETF,                 ///<ETF����ҵ����δ֧�֣�
	XTP_BUSINESS_TYPE_MARGIN,              ///<������ȯҵ����δ֧�֣�
	XTP_BUSINESS_TYPE_DESIGNATION,         ///<ת�йܣ�δ֧�֣�
	XTP_BUSINESS_TYPE_ALLOTMENT,		   ///<���ҵ�񣨶�Ӧ��price type��ѡ���޼�����,side��Ϊ��
	XTP_BUSINESS_TYPE_STRUCTURED_FUND_PURCHASE_REDEMPTION,	   ///<�ּ���������ҵ����δ֧�֣�
	XTP_BUSINESS_TYPE_STRUCTURED_FUND_SPLIT_MERGE,	   ///<�ּ������ֺϲ�ҵ����δ֧�֣�
	XTP_BUSINESS_TYPE_MONEY_FUND,		   ///<���һ���ҵ����δ֧�֣�
	XTP_BUSINESS_TYPE_UNKNOWN              ///<δ֪����

};


/////////////////////////////////////////////////////////////////////////
///@enum XTP_FUND_TRANSFER_TYPE ���ʽ���ת��������
/////////////////////////////////////////////////////////////////////////
enum XTP_FUND_TRANSFER_TYPE
{
    XTP_FUND_TRANSFER_OUT = 0,		///<ת�� ��XTPת������̨
    XTP_FUND_TRANSFER_IN,	        ///<ת�� �ӹ�̨ת��XTP
    XTP_FUND_TRANSFER_UNKNOWN
};

/////////////////////////////////////////////////////////////////////////
///@enum XTP_FUND_OPER_STATUS ��̨�ʽ�������
/////////////////////////////////////////////////////////////////////////
enum XTP_FUND_OPER_STATUS {
    XTP_FUND_OPER_PROCESSING = 0, ///<XOMS���յ������ڴ�����
    XTP_FUND_OPER_SUCCESS,
    XTP_FUND_OPER_FAILED,
    XTP_FUND_OPER_SUBMITTED, ///<���ύ�����й�̨����
    XTP_FUND_OPER_UNKNOWN
};



/////////////////////////////////////////////////////////////////////////
///TXTPTradeTypeType�ǳɽ���������
/////////////////////////////////////////////////////////////////////////
typedef char TXTPTradeTypeType;

///��ͨ�ɽ�
#define XTP_TRDT_Common '0'
///��Ȩִ��
#define XTP_TRDT_OptionsExecution '1'
///OTC�ɽ�
#define XTP_TRDT_OTC '2'
///��ת�������ɽ�
#define XTP_TRDT_EFPDerived '3'
///��������ɽ�
#define XTP_TRDT_CombinationDerived '4'
///ETF�깺
#define XTP_TRDT_EFTPurchase '5'
///ETF���
#define XTP_TRDT_EFTRedem '6'

/////////////////////////////////////////////////////////////////////////
///TXTPOrderTypeType�Ǳ�����������
/////////////////////////////////////////////////////////////////////////
typedef char TXTPOrderTypeType;

///����
#define XTP_ORDT_Normal '0'
///��������
#define XTP_ORDT_DeriveFromQuote '1'
///�������
#define XTP_ORDT_DeriveFromCombination '2'
///��ϱ���
#define XTP_ORDT_Combination '3'
///������
#define XTP_ORDT_ConditionalOrder '4'
///������
#define XTP_ORDT_Swap '5'


#pragma pack()

#endif
